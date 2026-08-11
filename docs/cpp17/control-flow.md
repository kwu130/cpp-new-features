# 结构化绑定与条件语句增强

结构化绑定可以为数组、元组和类似结构体的成员命名。`if`/`switch` 初始化语句缩短临时对象作用域，`if constexpr` 则在编译期丢弃不适用分支。

<!-- example id="cpp17-control-flow" std="c++17" file="main.cpp" kind="single" compilers="all" output="answer=42" -->
```cpp
#include <iostream>
#include <map>
#include <string>
#include <type_traits>
#include <utility>

template <typename T>
void print_value(const T& value) {
    if constexpr (std::is_integral_v<T>) {
        std::cout << "answer=" << value << '\n';
    } else {
        std::cout << value << '\n';
    }
}

int main() {
    std::map<std::string, int> values{{"answer", 42}};
    if (const auto iterator = values.find("answer"); iterator != values.end()) {
        const auto& [name, value] = *iterator;
        (void)name;
        print_value(value);
    }
}
```

结构化绑定使用 `auto`、`auto&` 或 `const auto&` 时同样需要考虑复制。`if constexpr` 只会丢弃依赖模板参数的不适用代码，它不是普通运行期条件的替代品。

