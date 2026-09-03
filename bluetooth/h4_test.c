#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <termios.h>
#include <sys/select.h>

int main(int argc, char **argv)
{
	const char *dev = "/dev/ttyAML6";
	int fd;
	struct termios tio;
	uint8_t cmd[] = { 0x01, 0x01, 0x10, 0x00 };
	uint8_t buf[256];
	ssize_t n;
	fd_set rfds;
	struct timeval tv;

	if (argc > 1)
		dev = argv[1];

	fd = open(dev, O_RDWR | O_NOCTTY);
	if (fd < 0) {
		perror("open");
		return 1;
	}

	if (tcflush(fd, TCIOFLUSH) < 0)
		perror("tcflush");

	if (tcgetattr(fd, &tio) < 0) {
		perror("tcgetattr");
		close(fd);
		return 1;
	}

	cfmakeraw(&tio);

	tio.c_cflag &= ~(CSIZE | PARENB | PARODD | CSTOPB);
	tio.c_cflag |= CS8 | CLOCAL | CREAD | CRTSCTS;

	if (cfsetispeed(&tio, B115200) < 0 ||
	    cfsetospeed(&tio, B115200) < 0) {
		perror("cfset speed");
		close(fd);
		return 1;
	}

	if (tcsetattr(fd, TCSANOW, &tio) < 0) {
		perror("tcsetattr");
		close(fd);
		return 1;
	}

	tcflush(fd, TCIOFLUSH);

	printf("UART: %s\n", dev);
	printf("Config: 115200 8N1 RTS/CTS\n");

	printf("TX:");
	for (size_t i = 0; i < sizeof(cmd); i++)
		printf(" %02x", cmd[i]);
	printf("\n");

	n = write(fd, cmd, sizeof(cmd));
	if (n < 0) {
		perror("write");
		close(fd);
		return 1;
	}

	if (tcdrain(fd) < 0)
		perror("tcdrain");

	FD_ZERO(&rfds);
	FD_SET(fd, &rfds);

	tv.tv_sec = 2;
	tv.tv_usec = 0;

	int ret = select(fd + 1, &rfds, NULL, NULL, &tv);

	if (ret < 0) {
		perror("select");
		close(fd);
		return 1;
	}

	if (ret == 0) {
		printf("RX timeout: no data received\n");
		close(fd);
		return 2;
	}

	n = read(fd, buf, sizeof(buf));

	if (n < 0) {
		perror("read");
		close(fd);
		return 1;
	}

	printf("RX (%zd bytes):", n);
	for (ssize_t i = 0; i < n; i++)
		printf(" %02x", buf[i]);
	printf("\n");

	close(fd);
	return 0;
}