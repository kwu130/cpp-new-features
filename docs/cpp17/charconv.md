# `from_chars` 与 `to_chars`

字符转换接口不依赖区域设置、不分配内存，也不通过异常报告普通解析失败，适合高性能协议和文本处理。

<!-- example id="cpp17-charconv" std="c++17" file="main.cpp" kind="single" compilers="all" output="value=42, hex=2a" -->
```cpp
#include <array>
#include <charconv>
#include <iostream>
#include <string_view>

int main() {
    constexpr std::string_view input = "42";
    int value = 0;
    const auto parsed = std::from_chars(input.data(), input.data() + input.size(), value);
    if (parsed.ec != std::errc{} || parsed.ptr != input.data() + input.size()) {
        return 1;
    }

    std::array<char, 16> buffer{};
    const auto written = std::to_chars(buffer.data(), buffer.data() + buffer.size(), value, 16);
    if (written.ec != std::errc{}) {
        return 1;
    }
    std::cout << "value=" << value << ", hex="
              << std::string_view(buffer.data(), static_cast<std::size_t>(written.ptr - buffer.data())) << '\n';
}
```

`from_chars` 不会自动要求消费完整输入，调用者应同时检查错误码和返回指针。浮点字符转换虽然属于 C++17，但早期标准库实现支持较晚，跨工具链时应特别验证。

