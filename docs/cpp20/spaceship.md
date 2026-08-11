# 三路比较运算符

`<=>` 一次表达小于、等于和大于关系。编译器可据此重写常见比较表达式，并为成员逐项生成一致的默认比较。

<!-- example id="cpp20-spaceship" std="c++20" file="main.cpp" kind="single" compilers="all" output="older=true, same=true" -->
```cpp
#include <compare>
#include <iostream>
#include <string>

struct Version {
    int major;
    int minor;
    auto operator<=>(const Version&) const = default;
};

int main() {
    const Version current{2, 1};
    const Version previous{1, 9};
    std::cout << std::boolalpha
              << "older=" << (previous < current)
              << ", same=" << (current == Version{2, 1}) << '\n';
}
```

默认比较按成员声明顺序进行。浮点成员可能使结果成为偏序，因为 NaN 不与任何值有序；自定义比较类别必须符合类型真实语义。

