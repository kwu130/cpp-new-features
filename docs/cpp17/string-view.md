# `string_view`

`string_view` 是不拥有字符数据的轻量视图，适合只读参数、解析切片和避免临时字符串分配。

<!-- example id="cpp17-string-view" std="c++17" file="main.cpp" kind="single" compilers="all" output="cpp17" -->
```cpp
#include <iostream>
#include <string>
#include <string_view>

std::string_view value_after(std::string_view text, char separator) {
    const auto position = text.find(separator);
    return position == std::string_view::npos ? std::string_view{} : text.substr(position + 1);
}

int main() {
    const std::string configuration = "standard=cpp17";
    const std::string_view value = value_after(configuration, '=');
    std::cout << value << '\n';
}
```

视图不延长底层字符串生命周期，也不保证以空字符结尾。不要返回指向局部 `std::string` 的视图；调用要求 C 字符串的 API 时应显式构造拥有数据的字符串。

