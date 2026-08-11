# Filesystem

`<filesystem>` 提供路径拼接、目录遍历和文件状态等跨平台接口，避免手写字符串路径与平台 API。

<!-- example id="cpp17-filesystem" std="c++17" file="main.cpp" kind="single" compilers="all" output="report.txt" -->
```cpp
#include <filesystem>
#include <iostream>

int main() {
    const std::filesystem::path directory = "reports";
    const std::filesystem::path file = directory / "daily" / "report.txt";
    std::cout << file.filename().string() << '\n';
}
```

路径应通过 `/` 运算符组合，不要手工拼接分隔符。真实文件操作可能失败，应使用异常接口或带 `std::error_code` 的重载处理权限、竞争和不存在等情况。

