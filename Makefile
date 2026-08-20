PS5_HOST ?= 192.168.0.208
PS5_PORT ?= 9021

ifdef PS5_PAYLOAD_SDK
    include $(PS5_PAYLOAD_SDK)/make/toolchain.mk
else
    $(error PS5_PAYLOAD_SDK is undefined)
endif

TARGET := ps5_livecontainer.elf
SRCS := src/main.c src/elf_loader.c src/signal_guard.c src/vfs_sandbox.c src/http_server.c src/ps5_notify.c src/video_out.c
OBJS := $(SRCS:.c=.o)

CFLAGS := -Wall -Wextra -Iinclude -D_BSD_SOURCE -pthread
LIBS := -lkernel_sys -lkernel -lSceSystemService -lSceNet -lpthread

all: $(TARGET) payloads

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LIBS)
	strip --strip-all $@

payloads:
	$(MAKE) -C test_payloads/hello_runner
	$(MAKE) -C test_payloads/crash_catcher
	$(MAKE) -C tools/notify

clean:
	rm -f $(TARGET) $(OBJS)
	$(MAKE) -C test_payloads/hello_runner clean
	$(MAKE) -C test_payloads/crash_catcher clean
	$(MAKE) -C tools/notify clean

deploy: $(TARGET)
	python scripts/deploy_payload.py
