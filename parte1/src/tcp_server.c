#include "protocol.h"
#include <omp.h>

static int reply(int fd, const char *s) {
	return send_all(fd, s, strlen(s));
}

static int put_file(int fd, const char *name, uint64_t size) {
	char temp[] = ".upload-XXXXXX";
	int raw = mkstemp(temp);
	if (raw < 0)
		return reply(fd, "ERR cannot-open\n");
	FILE *f = fdopen(raw, "wb");
	if (!f) {
		close(raw);
		unlink(temp);
		return reply(fd, "ERR cannot-open\n");
	}
	int ok = reply(fd, "READY\n") == 0;
	unsigned char buf[BLOCK];
	while (ok && size) {
		size_t n = size < sizeof buf ? (size_t)size : sizeof buf;
		if (recv_exact(fd, buf, n) || fwrite(buf, 1, n, f) != n)
			ok = 0;
		else
			size -= n;
	}
	if (fclose(f))
		ok = 0;
	if (!ok) {
		unlink(temp);
		return -1;
	}
	// Publica somente o arquivo completo. O último PUT concluído vence.
	// Leitores mantêm a versão aberta; um PUT interrompido preserva a anterior.
	if (rename(temp, name)) {
		unlink(temp);
		return reply(fd, "ERR rename\n");
	}
	return reply(fd, "OK\n");
}

static int get_file(int fd, const char *name) {
	int raw = open(name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK);
	struct stat st;
	if (raw < 0)
		return reply(fd, "ERR not-found\n");
	if (fstat(raw, &st) || !S_ISREG(st.st_mode) || st.st_size < 0 ||
		(uint64_t)st.st_size > MAX_SIZE) {
		close(raw);
		return reply(fd, "ERR file-type-size\n");
	}
	FILE *f = fdopen(raw, "rb");
	if (!f) {
		close(raw);
		return -1;
	}
	char head[80];
	int n = snprintf(head, sizeof head, "OK %" PRIu64 "\n", (uint64_t)st.st_size);
	int ok = send_all(fd, head, (size_t)n) == 0;
	uint64_t left = (uint64_t)st.st_size;
	unsigned char buf[BLOCK];
	while (ok && left) {
		size_t want = left < sizeof buf ? (size_t)left : sizeof buf;
		size_t got = fread(buf, 1, want, f);
		if (got != want || send_all(fd, buf, got))
			ok = 0;
		else
			left -= got;
	}
	fclose(f);
	return ok ? 0 : -1;
}

static void handle(int fd) {
	char line[1024];
	while (!read_line(fd, line, sizeof line)) {
		int r;
		if (!strncmp(line, "GET ", 4))
			r = valid_name(line + 4) ? get_file(fd, line + 4) : reply(fd, "ERR name\n");
		else if (!strncmp(line, "PUT ", 4)) {
			char *sep = strchr(line + 4, ' ');
			uint64_t size;
			if (!sep)
				r = reply(fd, "ERR syntax\n");
			else {
				*sep = 0;
				r = valid_name(line + 4) && !parse_size(sep + 1, &size)
					? put_file(fd, line + 4, size)
					: reply(fd, "ERR syntax\n");
			}
		} else if (!strcmp(line, "QUIT"))
			break;
		else if (!strncmp(line, "GET", 3) || !strncmp(line, "PUT", 3))
			r = reply(fd, "ERR syntax\n");
		else {
			r = reply(fd, line);
			if (!r)
				r = reply(fd, "\n");
		}
		if (r)
			break;
	}
	close(fd);
}

int main(int argc, char **argv) {
	if (argc != 3) {
		fprintf(stderr, "usage: %s PORT STORAGE_DIRECTORY\n", argv[0]);
		return 2;
	}
	int port = port_number(argv[1]);
	if (port < 0 || chdir(argv[2])) {
		perror("port/storage");
		return 2;
	}
	int srv = socket(AF_INET, SOCK_STREAM, 0), one = 1;
	if (srv < 0) {
		perror("socket");
		return 1;
	}
	setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
	struct sockaddr_in a = {.sin_family = AF_INET,
		.sin_port = htons((uint16_t)port),
		.sin_addr.s_addr = htonl(INADDR_ANY)};
	if (bind(srv, (struct sockaddr *)&a, sizeof a) || listen(srv, 128)) {
		perror("listen");
		close(srv);
		return 1;
	}
	omp_set_dynamic(0);
	setvbuf(stdout, NULL, _IOLBF, 0);
	printf("LISTEN port=%d workers=8\n", port);
	// Cada trabalhador aceita e atende sua conexão, sem contador compartilhado
	// nem escalonamento do accept bloqueante como tarefa OpenMP.
#pragma omp parallel num_threads(8) shared(srv)
	{
		for (;;) {
			int fd = accept(srv, NULL, NULL);
			if (fd < 0) {
				if (errno == EINTR)
					continue;
				perror("accept");
				break;
			}
			if (setup_socket(fd)) {
				close(fd);
				continue;
			}
			printf("ACCEPT worker=%d\n", omp_get_thread_num());
			handle(fd);
		}
	}
	close(srv);
	return 1;
}
