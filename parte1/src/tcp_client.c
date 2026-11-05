#include "protocol.h"

static double monotonic(void) {
	struct timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec + t.tv_nsec / 1e9;
}

static int connect_timeout(int fd, const struct sockaddr_in *a) {
	int flags = fcntl(fd, F_GETFL, 0);
	if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK))
		return -1;
	int r = connect(fd, (const struct sockaddr *)a, sizeof *a);
	if (r < 0) {
		if (errno != EINPROGRESS)
			return -1;
		struct pollfd p = {.fd = fd, .events = POLLOUT};
		do {
			r = poll(&p, 1, 15000);
		} while (r < 0 && errno == EINTR);
		if (r <= 0) {
			errno = ETIMEDOUT;
			return -1;
		}
		int err = 0;
		socklen_t len = sizeof err;
		if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &err, &len) || err) {
			if (err)
				errno = err;
			return -1;
		}
	}
	return fcntl(fd, F_SETFL, flags);
}

static int transfer(int fd, int put, const char *remote, const char *local, uint64_t *bytes) {
	char head[1024], temp[4096];
	unsigned char buf[BLOCK];
	uint64_t left;
	FILE *f = NULL;
	if (put) {
		int raw = open(local, O_RDONLY | O_NONBLOCK);
		struct stat st;
		if (raw < 0)
			return -1;
		if (fstat(raw, &st) || !S_ISREG(st.st_mode) || st.st_size < 0 ||
			(uint64_t)st.st_size > MAX_SIZE) {
			close(raw);
			return -1;
		}
		f = fdopen(raw, "rb");
		if (!f) {
			close(raw);
			return -1;
		}
		left = (uint64_t)st.st_size;
		int n = snprintf(head, sizeof head, "PUT %s %" PRIu64 "\n", remote, left);
		if (send_all(fd, head, (size_t)n) || read_line(fd, head, sizeof head) ||
			strcmp(head, "READY")) {
			fclose(f);
			return -1;
		}
	} else {
		int n = snprintf(head, sizeof head, "GET %s\n", remote);
		if (send_all(fd, head, (size_t)n) || read_line(fd, head, sizeof head) ||
			strncmp(head, "OK ", 3) || parse_size(head + 3, &left))
			return -1;
		n = snprintf(temp, sizeof temp, "%s.part-XXXXXX", local);
		if (n < 0 || (size_t)n >= sizeof temp)
			return -1;
		int raw = mkstemp(temp);
		if (raw < 0)
			return -1;
		f = fdopen(raw, "wb");
		if (!f) {
			close(raw);
			unlink(temp);
			return -1;
		}
	}
	int ok = 1;
	while (left) {
		size_t n = left < sizeof buf ? (size_t)left : sizeof buf;
		if (put) {
			if (fread(buf, 1, n, f) != n || send_all(fd, buf, n)) {
				ok = 0;
				break;
			}
		} else if (recv_exact(fd, buf, n) || fwrite(buf, 1, n, f) != n) {
			ok = 0;
			break;
		}
		*bytes += n;
		left -= n;
	}
	if (fclose(f))
		ok = 0;
	if (put) {
		if (ok && (read_line(fd, head, sizeof head) || strcmp(head, "OK")))
			ok = 0;
	} else {
		if (ok && rename(temp, local))
			ok = 0;
		if (!ok)
			unlink(temp);
	}
	return ok ? 0 : -1;
}

int main(int argc, char **argv) {
	if (argc != 6) {
		fprintf(stderr, "usage: %s IPv4 PORT GET|PUT REMOTE_NAME LOCAL_PATH\n", argv[0]);
		return 2;
	}
	int port = port_number(argv[2]), put = !strcmp(argv[3], "PUT");
	if (port < 0 || (!put && strcmp(argv[3], "GET")) || !valid_name(argv[4]))
		return 2;
	struct sockaddr_in a = {.sin_family = AF_INET, .sin_port = htons((uint16_t)port)};
	if (inet_pton(AF_INET, argv[1], &a.sin_addr) != 1)
		return 2;
	const char *gate = getenv("T1_START_NS");
	if (gate) {
		char *end;
		errno = 0;
		unsigned long long ns = strtoull(gate, &end, 10);
		if (errno || *end)
			return 2;
		struct timespec deadline = {(time_t)(ns / 1000000000ULL), (long)(ns % 1000000000ULL)};
		int e;
		do {
			e = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &deadline, NULL);
		} while (e == EINTR);
		if (e)
			return 2;
	}
	double start = monotonic();
	uint64_t bytes = 0;
	int fd = socket(AF_INET, SOCK_STREAM, 0), ok = 0;
	if (fd >= 0 && !setup_socket(fd) && !connect_timeout(fd, &a))
		ok = transfer(fd, put, argv[4], argv[5], &bytes) == 0;
	if (fd >= 0)
		close(fd);
	double elapsed = monotonic() - start;
	printf("{\"operation\":\"%s\",\"bytes\":%" PRIu64
			",\"start_s\":%.9f,\"duration_s\":%.9f,\"throughput_mbps\":%.9f,\"status\":\"%s\"}\n",
		argv[3], bytes, start, elapsed, elapsed > 0 ? bytes * 8.0 / elapsed / 1e6 : 0,
		ok ? "ok" : "error");
	return ok ? 0 : 1;
}
