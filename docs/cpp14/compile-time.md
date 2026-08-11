# 变量模板与放宽的 `constexpr`

变量模板为一族类型提供变量定义。C++14 的 `constexpr` 函数允许局部变量、循环和分支，使编译期算法更接近日常代码。

<!-- example id="cpp14-compile-time" std="c++14" file="main.cpp" kind="single" compilers="all" output="55" -->
```cpp
#include <iostream>
#include <type_traits>

template <typename T>
constexpr T zero = T{0};

constexpr int sum_to(int limit) {
    int result = 0;
    for (int value = 1; value <= limit; ++value) {
        result += value;
    }
    return result;
}

int main() {
    constexpr int result = sum_to(10) + zero<int>;
    static_assert(result == 55, "compile-time loop must work");
    static_assert(std::is_same<decltype(zero<long>), const long>::value,
                  "a constexpr variable is const");
    std::cout << result << '\n';
}
```

命名空间作用域的变量模板与普通模板一样可能涉及多翻译单元定义问题；C++17 的内联变量提供了更直接的处理方式。

