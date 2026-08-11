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

## `<bit>` 提供的能力

位工具包括 `popcount`、`countl_zero/one`、`countr_zero/one`、`rotl/rotr`、`has_single_bit`、`bit_floor/ceil/width`，以及检查本机字节序的 `endian`。它们只接受规定的无符号整数类型，避免有符号移位和算术右移的语义陷阱。

标准定义可移植结果，编译器通常将其识别为内建并映射到目标 CPU 的计数或旋转指令；没有硬件指令时生成等价序列。调用者不应假设一定单指令，也不必手写难以审查的位技巧来追求同样优化。

## 边界语义

手写“数前导零”常在输入 0 时触发未定义内建行为，标准函数为零定义明确结果。旋转会按位宽规范化移位量，避免普通移位等于或超过位宽的未定义行为。

`bit_ceil(x)` 返回不小于 x 的最小二次幂；x 为 0 时结果为 1，但若结果超出类型表示范围则不安全。容量增长算法必须先做上限检查。

## 数学常量

`std::numbers::pi_v<T>` 等变量模板按浮点类型提供常量，`pi` 是 double 便捷别名。它们避免手写精度不足或不同文件常量不一致。整数类型不适合直接实例化这些浮点数学常量。

常量精度受目标浮点类型限制，不会自动提供任意精度数学。数值算法还需处理舍入模式、误差传播和平台数学函数差异。

## 示例解析与实践

示例用 `popcount` 统计四个置位，`bit_ceil` 把容量 13 上取整为 16，并验证标准 π 范围。工程中优先标准位工具，所有容量计算检查溢出，协议代码显式固定宽度与字节序，数值测试使用容差而非直接等号。
