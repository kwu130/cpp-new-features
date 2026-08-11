# 范围 `for`

范围 `for` 直接遍历数组或提供 `begin`/`end` 的对象，消除了手写迭代器边界的样板代码。

<!-- example id="cpp11-range-for" std="c++11" file="main.cpp" kind="single" compilers="all" output="2 4 6" -->
```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3};
    for (auto& value : values) {
        value *= 2;
    }

    for (const auto& value : values) {
        std::cout << value << (value == values.back() ? '\n' : ' ');
    }
}
```

只读遍历通常写成 `const auto&`，原地修改写成 `auto&`。直接写 `auto` 会复制每个元素。遍历期间不要执行可能使当前迭代器失效的容器修改操作。

