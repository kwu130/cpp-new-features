# if consteval 与 constexpr 的进一步放宽

阅读前建议先了解：[C++20 编译期计算](../cpp20/compile-time.md)、[独占所有权](../cpp11/smart-pointers.md)。本篇介绍的新增能力属于 C++23。

## 区分两种求值路径

一个 constexpr 函数可能被用来计算常量，也可能处理程序运行时才知道的输入。`if consteval` 让函数为这两种情况选择不同路径，例如常量计算时调用另一个 consteval 函数，运行时执行普通算法。

C++20 的 `is_constant_evaluated()` 能查询当前是否在常量求值，但普通 if 不会获得调用立即函数的特殊规则。C++23 的 `if consteval` 真分支具有这种规则，正式名称是“立即函数上下文”；下面通过传入函数参数展示它的用途。

传统判断与新判断的区别，见下列语法片段：

```text
if (std::is_constant_evaluated()) { /* 普通 if，不建立立即上下文 */ }
if consteval { /* 立即上下文 */ } else { /* 运行期路径 */ }
```

## 最小示例：相同数值，两条合法路径

```cpp example id="cpp23-if-consteval" std="c++23" file="main.cpp" kind="single" compilers="all" output="compile=6, runtime=8" requires="__cpp_if_consteval>=202106"
#include <iostream>
consteval int immediate_twice(int value) { return value * 2; }
constexpr int twice(int value) {
    if consteval {
        return immediate_twice(value);
    } else {
        return value * 2;
    }
}
static_assert(twice(3) == 6);
int main() {
    constexpr int compiled = twice(3);
    int input = 4;
    int runtime = twice(input);
    std::cout << "compile=" << compiled << ", runtime=" << runtime << '\n';
}
```

编译期初始化 compiled 时进入第一分支；普通运行期调用进入第二分支。两个分支实现相同乘二行为。优化器可能折叠运行期调用，但不会把它的语言求值上下文改成第一分支。if consteval 需要大括号，没有括号条件；也可写 if !consteval 反转两条路径。

if constexpr 按编译期条件丢弃模板分支，if consteval 按求值上下文选择路径，两者用途不同。两边仍须满足相应语义检查，不能靠它把任意不合法代码藏起来。

## constexpr unique_ptr：编译期临时拥有资源

C++23 进一步允许 unique_ptr 的许多操作用于常量求值。以前计算常量通常使用直接局部值或数组；若现有算法围绕独占对象组织，现在可在求值期间分配并释放。

```cpp example id="cpp23-constexpr-unique-ptr" std="c++23" file="main.cpp" kind="single" compilers="all" output="value=42" requires="__cpp_lib_constexpr_memory>=202202"
#include <iostream>
#include <memory>
constexpr int answer() {
    auto value = std::make_unique<int>(42);
    return *value;
}
static_assert(answer() == 42);
int main() { std::cout << "value=" << answer() << '\n'; }
```

指针离开函数时释放对象，常量求值中没有遗留分配；保存下来的是整数。不要写一个指向此次编译期动态分配的全局 constexpr unique_ptr，让分配逃出常量求值。

## 放宽限制不等于所有代码都可编译期执行

C++23 放宽 constexpr 函数体对部分声明的限制，并允许满足条件的 static constexpr 局部变量。某些声明可以出现在函数体中，实际常量求值仍不能经过禁止的操作；文件 I/O、任意分配生命周期和运行期状态不会自动获得编译期意义。

适合统一编译期与运行期的纯计算，或复用以 RAII 表达的计算流程。只需乘二时直接返回整数更简单，本例的动态分配用于说明边界，不是性能建议。编译期计算也有编译耗时与资源成本。

## 权威资料

- [if consteval](https://eel.is/c++draft/stmt.if)、[常量表达式](https://eel.is/c++draft/expr.const)
- [P1938R3：if consteval](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p1938r3.html)
- [P2273R3：constexpr unique_ptr](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p2273r3.pdf)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/compile-time.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
