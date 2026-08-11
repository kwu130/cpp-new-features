# Concepts 与约束

Concepts 为模板参数声明可读、可组合的约束，让重载选择更明确，也能把模板错误定位到接口边界。

<!-- example id="cpp20-concepts" std="c++20" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <concepts>
#include <iostream>

template <typename T>
concept Arithmetic = std::integral<T> || std::floating_point<T>;

template <Arithmetic T>
T twice(T value) {
    return value + value;
}

template <typename T>
requires std::integral<T> && (sizeof(T) >= 4)
T add(T left, T right) {
    return left + right;
}

int main() {
    static_assert(Arithmetic<double>);
    std::cout << add(twice(10), 22) << '\n';
}
```

Concept 应描述调用者真正依赖的语义能力，而不是只罗列碰巧使用的具体类型。优先复用标准 Concept，并把复杂约束拆成有业务含义的命名 Concept。

