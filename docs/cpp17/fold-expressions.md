# 折叠表达式

折叠表达式用一个运算符归约参数包，取代 C++11 中常见的递归模板和展开技巧。

<!-- example id="cpp17-fold-expressions" std="c++17" file="main.cpp" kind="single" compilers="all" output="10" -->
```cpp
#include <iostream>

template <typename... Values>
auto sum(Values... values) {
    return (values + ... + 0);
}

template <typename... Conditions>
bool all(Conditions... conditions) {
    return (conditions && ...);
}

int main() {
    if (!all(true, 2 < 3, 4 == 4)) {
        return 1;
    }
    std::cout << sum(1, 2, 3, 4) << '\n';
}
```

一元折叠对空参数包只为 `&&`、`||` 和逗号运算符定义了单位值。需要支持空包时，像示例一样提供初始值。对非结合运算符还必须明确左折叠与右折叠的差异。

