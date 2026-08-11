# 指定初始化

指定初始化用成员名初始化聚合对象，配置结构体因此更易读，也不再依赖读者记住每个值的位置。

<!-- example id="cpp20-designated-initialization" std="c++20" file="main.cpp" kind="single" compilers="all" output="localhost:8080 secure=false" -->
```cpp
#include <iostream>
#include <string>

struct ServerConfig {
    std::string host;
    int port = 80;
    bool secure = false;
};

int main() {
    const ServerConfig config{
        .host = "localhost",
        .port = 8080,
        .secure = false,
    };
    std::cout << config.host << ':' << config.port
              << " secure=" << std::boolalpha << config.secure << '\n';
}
```

C++20 要求指示符遵循成员声明顺序，且只适用于聚合类型；它不同于允许任意顺序的某些语言扩展。

