# 二进制字面量与数字分隔符

二进制字面量适合表达位掩码，单引号数字分隔符提高长数字的可读性且不改变数值。

<!-- example id="cpp14-literals" std="c++14" file="main.cpp" kind="single" compilers="all" output="mask=165, population=1000000" -->
```cpp
#include <iostream>

int main() {
    const unsigned mask = 0b1010'0101;
    const int population = 1'000'000;
    std::cout << "mask=" << mask << ", population=" << population << '\n';
}
```

分隔符可以出现在整数和浮点字面量的数字之间，但不能紧邻小数点或指数标记。位操作仍应优先使用无符号类型，避免有符号移位带来的边界问题。

