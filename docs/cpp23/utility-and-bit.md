# 实用工具：枚举、字节序、转发与不可达分支

阅读前建议先了解：[位运算](../cpp20/bit-and-numbers.md)、[移动与转发](../cpp11/move-semantics.md)。本篇介绍的新增能力属于 C++23。

## 用库接口表达已有意图

C++23 增加几个小工具，替代枚举类型强转、手写字节交换和复杂引用类型拼接。它们彼此独立，不需要组合成一个大程序。先读枚举与字节序；forward_like 需要值类别知识，unreachable 需要证明控制流前置条件。

## to_underlying：取得枚举的底层值

过去需写 `static_cast<std::underlying_type_t<Mode>>(mode)`。to_underlying 返回枚举声明的底层整数类型，避免在接口变化后仍手写旧类型。

```cpp example id="cpp23-to-underlying" std="c++23" file="main.cpp" kind="single" compilers="all" output="mode=2" requires="__cpp_lib_to_underlying>=202102"
#include <iostream>
#include <type_traits>
#include <utility>
enum class Mode : unsigned { read = 1, write = 2 };
int main() {
    static_assert(std::is_same_v<decltype(std::to_underlying(Mode::write)), unsigned>);
    std::cout << "mode=" << std::to_underlying(Mode::write) << '\n';
}
```

它不验证整数是否对应枚举值，也不做反向转换。序列化时还要确定协议长度与端序；底层类型不是整个协议。

## byteswap：反转整数的字节顺序

手写移位与掩码容易遗漏宽度。byteswap 对符合要求的整数反转字节次序，不反转各字节内的位；也不会自动探测网络协议。

```cpp example id="cpp23-byteswap" std="c++23" file="main.cpp" kind="single" compilers="all" output="swapped=4030201" requires="__cpp_lib_byteswap>=202110"
#include <bit>
#include <cstdint>
#include <iomanip>
#include <iostream>
int main() {
    constexpr std::uint32_t source = 0x01020304;
    constexpr auto result = std::byteswap(source);
    static_assert(result == 0x04030201);
    std::cout << "swapped=" << std::hex << result << '\n';
}
```

值结果与本机内存端序无关；若要按协议编码，结合 C++20 endian 判断是否需要交换。接口要求整数类型且不带填充位；结构体、浮点数不能直接传入。不要通过违反别名规则的指针强转来绕开类型要求。

## forward_like：按另一个类型的性质转发

std::forward<T> 依据参数推导出的 T 转发。forward_like<Model>(value) 则把 Model 的 const 与左值/右值性质应用到 value，适合按调用对象性质访问其成员。

```cpp example id="cpp23-forward-like" std="c++23" file="main.cpp" kind="single" compilers="all" output="value=7" requires="__cpp_lib_forward_like>=202207"
#include <iostream>
#include <type_traits>
#include <utility>
int main() {
    int value = 7;
    static_assert(std::is_same_v<decltype(std::forward_like<const int&>(value)), const int&>);
    static_assert(std::is_same_v<decltype(std::forward_like<int&&>(value)), int&&>);
    std::cout << "value=" << std::forward_like<const int&>(value) << '\n';
}
```

这里两个表达式只是类型转换，不执行移动；真正的资源转移取决于后续重载。它合并 const 并匹配引用类别，不能笼统说复制所有 cv 修饰，尤其不传播 Model 的 volatile。Model 通常来自 [显式对象参数](explicit-object-parameter.md) 的推导类型。

返回成员引用时仍依赖原对象存活。给临时对象内部成员转发出右值引用，不会让该成员延长寿命。

工具链提示：Clang 配合使用推导返回类型实现 `forward_like` 的标准库（例如 libstdc++ 14）时，可能报“deduced return type cannot be used before it is defined”。这是 Clang 内建优化与库实现的兼容问题，见 [LLVM #64029](https://github.com/llvm/llvm-project/issues/64029)。本仓库对 Clang 的此类示例添加 `-fno-builtin-std-forward_like`，让编译器实例化标准库中的真实定义；示例仍检查原来的引用类型和输出，不替换实现或跳过验证。

## unreachable：只有已经证明的分支才能使用

传统代码用 assert(false)、抛异常或返回错误处理不可能情况；unreachable 告诉实现执行不会到达这里。执行到它是未定义行为，不能用于验证不可信输入，也不能替代错误处理。

```text
switch (verified_mode) {
case Mode::read:  return read_value();
case Mode::write: return write_value();
}
std::unreachable(); // 仅在接口已保证 verified_mode 只可能是上面两值时成立
```

本篇不运行违反该前置条件的程序。枚举对象也可能携带未列举值，所以仅因 switch 列出了所有命名枚举就使用 unreachable 并不充分。需要运行期防御时返回错误或抛异常更合适。

## 权威资料

- [utility：to_underlying、forward_like](https://eel.is/c++draft/utility)
- [byteswap](https://eel.is/c++draft/bit.byteswap)、[unreachable](https://eel.is/c++draft/utility.undefined)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/utility-and-bit.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
