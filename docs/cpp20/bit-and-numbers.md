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

这些函数大多是 `constexpr`，可同时用于静态断言、表大小计算和运行期热路径。重载只为标准无符号整数类型参与，传有符号数应先经过经过审查的显式转换，避免负值含义混乱。

<!-- example id="cpp20-bit-operations" std="c++20" file="main.cpp" kind="single" compilers="all" output="width=8, floor=128, rotated=3" -->
```cpp
#include <bit>
#include <cstdint>
#include <iostream>

int main() {
    constexpr std::uint8_t value = 0b1000'0001;
    constexpr int width = std::bit_width(value);
    constexpr auto floor = std::bit_floor(value);
    constexpr auto rotated = std::rotl(value, 1);

    static_assert(width == 8);
    static_assert(floor == 128);
    static_assert(rotated == 3);
    std::cout << "width=" << width
              << ", floor=" << static_cast<unsigned>(floor)
              << ", rotated=" << static_cast<unsigned>(rotated) << '\n';
}
```

`bit_width` 返回表示非零值所需位数；`bit_floor` 返回不大于输入的最高二次幂；8 位值左旋一位把最高位绕回最低位，得到二进制 `0000'0011`。旋转按类型位宽工作，因此先选择固定宽度类型很重要。

### 计数函数

`countl_zero/one` 从最高有效位方向计数连续相同位，`countr_zero/one` 从最低位方向计数，返回 int。对零输入，`countl_zero` 和 `countr_zero` 返回类型位数，避免编译器内建常见的零输入未定义陷阱。

`popcount` 返回置位总数，与连续计数不同。位图基数、权限集合和稀疏掩码常用它，但对大数组仍要批量遍历，单个整数函数不会自动向量化整个缓冲区。

### 二次幂工具

`has_single_bit(x)` 在 x 恰为正二次幂时为真；零为假。`bit_floor(0)` 返回 0，`bit_ceil(0/1)` 返回 1，`bit_width(0)` 返回 0。明确零边界能替代大量易错手写表达式。

`bit_ceil` 溢出是必须在调用前处理的前置条件问题。容量算法可先比较输入与 `1 << (digits - 1)` 等安全上限，或在更宽无符号类型中计算并验证回转。

## `bit_cast`

`bit_cast<To>(from)` 在两类型大小相同且满足 trivially copyable 等要求时复制对象表示，通常可优化成寄存器移动。它替代许多通过指针 reinterpret_cast 读取浮点位模式的严格别名违规写法。

结果值仍受目标类型可表示对象状态、填充位和不确定位规则约束。它不做数值转换，不改变字节序，也不允许大小不同。协议解码通常需要先排列字节，再 bit_cast 到目标表示，并验证平台浮点/整数假设。

对指针、含填充结构或具有多个表示的类型，不应仅因 trivially copyable 就把 bit_cast 结果持久化。跨进程格式要逐字段编码。

## `endian`

`endian::native` 可与 `little`、`big` 比较，帮助选择字节交换路径。标准也允许混合字节序平台，使 native 既不等于二者；可移植代码要有静态拒绝或通用分支。

C++20 `<bit>` 尚没有 C++23 的 `byteswap`。需要字节交换时可用经过测试的 constexpr 实现或平台内建，并把最低版本写清楚，不能在 C++20 示例中直接调用 `std::byteswap`。

## 边界语义

手写“数前导零”常在输入 0 时触发未定义内建行为，标准函数为零定义明确结果。旋转会按位宽规范化移位量，避免普通移位等于或超过位宽的未定义行为。

`bit_ceil(x)` 返回不小于 x 的最小二次幂；x 为 0 时结果为 1，但若结果超出类型表示范围则不安全。容量增长算法必须先做上限检查。

## 数学常量

`std::numbers::pi_v<T>` 等变量模板按浮点类型提供常量，`pi` 是 double 便捷别名。它们避免手写精度不足或不同文件常量不一致。整数类型不适合直接实例化这些浮点数学常量。

常量精度受目标浮点类型限制，不会自动提供任意精度数学。数值算法还需处理舍入模式、误差传播和平台数学函数差异。

除 pi 外还包括 e、log2e、log10e、ln2、ln10、sqrt2、sqrt3、phi 等常见常量及倒数/派生值。`name_v<T>` 是变量模板，便利名 `name` 等价于 double 特化。

模板参数必须是标准支持的浮点类型或实现扩展允许类型；尝试 `pi_v<int>` 不表达“整数 3”，而是不合适的实例化。泛型数值算法用与计算类型相同的 `pi_v<T>`，避免先从 double 转换造成不必要精度限制。

这些常量是正确舍入到目标类型能力范围的编译期值，但算法结果仍受操作顺序和数学函数实现影响。角度转换可用 pi 构造比例，比较结果继续使用误差模型而非精确相等。

## 示例解析与实践

示例用 `popcount` 统计四个置位，`bit_ceil` 把容量 13 上取整为 16，并验证标准 π 范围。工程中优先标准位工具，所有容量计算检查溢出，协议代码显式固定宽度与字节序，数值测试使用容差而非直接等号。

## 权威资料

- [P0631R8：数学常量](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p0631r8.pdf)
- [P0553R4：位运算](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p0553r4.html)
- [工作草案：Bit manipulation](https://eel.is/c++draft/bit)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
