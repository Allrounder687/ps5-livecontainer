PS5_HOST ?= ps5
PS5_PORT ?= 9021

ifdef PS5_PAYLOAD_SDK
    include $(PS5_PAYLOAD_SDK)/make/toolchain.mk
else
    $(error PS5_PAYLOAD_SDK is undefined)
endif

TARGET := ps5_livecontainer.elf
SRCS := src/main.c
OBJS := $(SRCS:.c=.o)

CFLAGS := -Wall -Wextra -Iinclude -D_BSD_SOURCE
LIBS := -lkernel_sys -lkernel -lSceSystemService

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
	$(PS5_DEPLOY) -h $(PS5_HOST) -p $(PS5_PORT) $(TARGET)
