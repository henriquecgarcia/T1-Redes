#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <sys/socket.h>
static _Thread_local unsigned ticks;
ssize_t send(int fd, const void *buf, size_t len, int flags) {
	static _Thread_local ssize_t (*real_send)(int, const void *, size_t, int);
	if (!real_send)
		*(void **)(&real_send) = dlsym(RTLD_NEXT, "send");
	if (++ticks % 37 == 0) {
		errno = EINTR;
		return -1;
	}
	return real_send(fd, buf, len > 4093 ? 4093 : len, flags);
}
ssize_t recv(int fd, void *buf, size_t len, int flags) {
	static _Thread_local ssize_t (*real_recv)(int, void *, size_t, int);
	if (!real_recv)
		*(void **)(&real_recv) = dlsym(RTLD_NEXT, "recv");
	if (++ticks % 37 == 0) {
		errno = EINTR;
		return -1;
	}
	return real_recv(fd, buf, len > 257 ? 257 : len, flags);
}