# 内联变量与嵌套命名空间

内联变量允许在头文件中定义同一个变量而不违反单一定义规则。嵌套命名空间语法则缩短了多层命名空间声明。

<!-- example id="cpp17-inline-variables" std="c++17" file="main.cpp" kind="single" compilers="all" output="cpp-features:1" -->
```cpp
#include <iostream>
#include <string_view>

namespace project::config {
inline constexpr std::string_view name = "cpp-features";
inline int active_readers = 0;
}

int main() {
    ++project::config::active_readers;
    std::cout << project::config::name << ':'
              << project::config::active_readers << '\n';
}
```

`inline` 解决的是跨翻译单元定义问题，并不提供线程安全。可在编译期确定的配置值优先写成 `inline constexpr`。

