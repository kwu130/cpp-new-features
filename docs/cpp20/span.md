# `span`

`span` 是连续内存的非拥有视图，可以统一接收数组、`array`、`vector` 或指针加长度，同时保留元素类型和边界信息。

<!-- example id="cpp20-span" std="c++20" file="main.cpp" kind="single" compilers="all" output="10" -->
```cpp
#include <array>
#include <iostream>
#include <span>

int sum(std::span<const int> values) {
    int result = 0;
    for (const int value : values) {
        result += value;
    }
    return result;
}

int main() {
    const std::array<int, 4> values{1, 2, 3, 4};
    std::cout << sum(values) << '\n';
}
```

`span` 不拥有内存，底层数据销毁或容器重新分配后视图会失效。只读参数使用 `span<const T>`；固定长度接口可以使用 `span<T, N>` 在类型中表达大小。

