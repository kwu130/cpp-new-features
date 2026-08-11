# 位运算工具与数学常量

`<bit>` 提供旋转、位计数、二进制上取整等可读且可移植的操作；`<numbers>` 提供按浮点类型定义的数学常量。

<!-- example id="cpp20-bit-numbers" std="c++20" file="main.cpp" kind="single" compilers="all" output="ones=4, capacity=16, pi-valid=true" -->
```cpp
#include <bit>
#include <cstdint>
#include <iostream>
#include <numbers>

int main() {
    const std::uint32_t flags = 0b1010'1010;
    const int ones = std::popcount(flags);
    const unsigned capacity = std::bit_ceil(13U);
    const bool pi_valid = std::numbers::pi > 3.14 && std::numbers::pi < 3.15;
    std::cout << "ones=" << ones << ", capacity=" << capacity
              << ", pi-valid=" << std::boolalpha << pi_valid << '\n';
}
```

大多数位工具要求无符号整数。`bit_ceil` 的结果若无法由返回类型表示会触发未定义行为，调用前应限制输入范围。

