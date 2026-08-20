ifdef PS5_PAYLOAD_SDK
    include $(PS5_PAYLOAD_SDK)/make/toolchain.mk
else
    $(error PS5_PAYLOAD_SDK is undefined)
endif

TARGET := eboot.elf
SRCS := main.c
CFLAGS := -Wall -Wextra
LIBS := -lkernel_sys -lkernel -lSceSystemService

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LIBS)

clean:
	rm -f $(TARGET)
