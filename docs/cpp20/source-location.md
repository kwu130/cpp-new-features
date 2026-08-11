# `source_location`

`source_location` 以标准方式捕获调用点的文件、行号和函数名，适合日志、断言和诊断接口。

<!-- example id="cpp20-source-location" std="c++20" file="main.cpp" kind="single" compilers="all" output="message=ready, line-positive=true" -->
```cpp
#include <iostream>
#include <source_location>
#include <string_view>

void log(std::string_view message,
         const std::source_location location = std::source_location::current()) {
    std::cout << "message=" << message
              << ", line-positive=" << std::boolalpha << (location.line() > 0) << '\n';
}

int main() {
    log("ready");
}
```

默认参数必须在接口处调用 `current()` 才能取得调用者位置；若在函数体内调用，记录到的将是日志函数自身位置。文件路径可能包含构建环境信息，公开日志前应考虑脱敏。

