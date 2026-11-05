#ifndef PROTOCOL_H
#define PROTOCOL_H
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
#define MAX_SIZE (UINT64_C(1024) * 1024 * 1024)
#define BLOCK 65536
static int send_all(int fd, const void *buf, size_t len) {
	const unsigned char *p = buf;
	while (len) {
		ssize_t n = send(fd, p, len, MSG_NOSIGNAL);
		if (n < 0 && errno == EINTR)
			continue;
		if (n <= 0)
			return -1;
		p += n;
		len -= (size_t)n;
	}
	return 0;
}

static int recv_exact(int fd, void *buf, size_t len) {
	unsigned char *p = buf;
	while (len) {
		ssize_t n = recv(fd, p, len, 0);
		if (n < 0 && errno == EINTR)
			continue;
		if (n <= 0)
			return -1;
		p += n;
		len -= (size_t)n;
	}
	return 0;
}

static int read_line(int fd, char *buf, size_t cap) {
	size_t i = 0;
	while (i + 1 < cap) {
		unsigned char c;
		if (recv_exact(fd, &c, 1))
			return -1;
		if (c == '\n') {
			buf[i] = 0;
			return 0;
		}
		if (c == 0 || c == '\r')
			return -1;
		buf[i++] = (char)c;
	}
	return -1;
}

static int valid_name(const char *s) {
	if (!*s || strlen(s) > 255 || !strcmp(s, ".") || !strcmp(s, ".."))
		return 0;
	for (; *s; s++)
		if (!((*s >= 'a' && *s <= 'z') || (*s >= 'A' && *s <= 'Z') || (*s >= '0' && *s <= '9') ||
				*s == '.' || *s == '_' || *s == '-'))
			return 0;
	return 1;
}

static int parse_size(const char *s, uint64_t *v) {
	if (!*s)
		return -1;
	for (const char *p = s; *p; p++)
		if (*p < '0' || *p > '9')
			return -1;
	errno = 0;
	char *end;
	unsigned long long n = strtoull(s, &end, 10);
	if (errno || *end || n > MAX_SIZE)
		return -1;
	*v = n;
	return 0;
}

static int setup_socket(int fd) {
	struct timeval tv = {15, 0};
	int one = 1;
	return setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv) ||
		setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof tv) ||
		setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one);
}

static int port_number(const char *s) {
	uint64_t n;
	return parse_size(s, &n) || n == 0 || n > 65535 ? -1 : (int)n;
}
#endif
