#include <cstdint>
#include <iostream>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <cassert>
#include <unistd.h>

#define NPNR_PACKED_STRUCT(...) __VA_ARGS__ __attribute__((packed))

template <typename T> struct RelPtr
{
    int32_t offset;

    const T *get() const { return reinterpret_cast<const T *>(reinterpret_cast<const char *>(this) + offset); }

    const T &operator[](std::size_t index) const { return get()[index]; }

    const T &operator*() const { return *(get()); }

    const T *operator->() const { return get(); }

    RelPtr(const RelPtr &) = delete;
    RelPtr &operator=(const RelPtr &) = delete;
};

NPNR_PACKED_STRUCT(template <typename T> struct RelSlice {
    int32_t offset;
    uint32_t length;

    const T *get() const { return reinterpret_cast<const T *>(reinterpret_cast<const char *>(this) + offset); }

    const T &operator[](std::size_t index) const
    {
        assert(index < length);
        return get()[index];
    }

    const T *begin() const { return get(); }
    const T *end() const { return get() + length; }

    size_t size() const { return length; }
    ptrdiff_t ssize() const { return length; }

    const T &operator*() const { return *(get()); }

    const T *operator->() const { return get(); }

    RelSlice(const RelSlice &) = delete;
    RelSlice &operator=(const RelSlice &) = delete;
});

NPNR_PACKED_STRUCT(struct BlobPOD {
    uint32_t version;
    RelSlice<uint8_t> code;
});

int main(int argc, const char **argv) {
    if (argc == 1) {
        std::cerr << "Usage: ./bba_exec_test database.bin" << std::endl;
        return 1;
    }
    struct stat st;
    stat(argv[1], &st);
    size_t size = st.st_size;
    int fd = open(argv[1], O_RDONLY);
    auto &blob = *reinterpret_cast<const RelPtr<BlobPOD> *>(mmap(nullptr, size, PROT_EXEC | PROT_READ, MAP_SHARED, fd, 0));

    // Run on a few test values
    std::cerr << "blob version " << blob->version << std::endl;
    auto func = reinterpret_cast<uint32_t(*)(uint32_t)>(blob->code.get());
    for (int i = 0; i < 10; i++) {
        std::cerr << "fn(" << i << ") = " << func(i) << std::endl;
    }
    close(fd);
    return 0;
}
