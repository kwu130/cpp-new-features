# 折叠表达式

阅读前建议先了解：[C++11 参数包](../cpp11/templates.md)；理解递归展开后再比较折叠写法。本篇介绍的新增能力属于 C++17；后续版本差异会另行标注。

## 把一组参数连接起来

要让 `sum(1, 2, 3)` 得到 6，C++11/14 常用递归模板：每次取第一个参数，与剩余参数的和相加，还要为“没有剩余参数”写一个终止重载。

C++17 可以直接写 `return (values + ... + 0);`。省略号表示把包中的每个参数连接到表达式里。例如传入 `1, 2, 3`，展开结果是：

```text
1 + (2 + (3 + 0))
```

这种写法叫折叠表达式。它省去的是递归样板；加法、类型转换和溢出规则仍与普通表达式相同。

## 第一个完整示例

先看 `sum`：它用 `+` 连接参数，末尾的 0 保证 `sum()` 也有结果。再看 `all`：用 `&&` 连接条件，只有全部条件为真才返回 true。

```cpp example id="cpp17-fold-expressions" std="c++17" file="main.cpp" kind="single" compilers="all" output="10"
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
    if (sum() != 0 || !all() || !all(true, 2 < 3, 4 == 4)) {
        return 1;
    }
    std::cout << sum(1, 2, 3, 4) << '\n';
}
```

输出为 `10`，因为 `sum(1, 2, 3, 4)` 展开为 `1 + (2 + (3 + (4 + 0)))`。程序还检查了空参数调用：`sum()` 为 0，`all()` 为 true。

固定的两个数直接相加即可。折叠适合模板需要处理任意数量实参的情况，例如累加、组合条件或逐项调用。

## 为什么要区分左右折叠

减法能看出差别：`(20 - 3) - 2` 为 15，而 `20 - (3 - 2)` 为 19。折叠方向决定括号如何嵌套。

```cpp example id="cpp17-fold-direction" std="c++17" file="main.cpp" kind="single" compilers="all" output="left=15, right=19"
#include <iostream>

template <typename... Values>
int subtract_from_twenty(Values... values) {
    return (20 - ... - values);
}

template <typename... Values>
int subtract_toward_two(Values... values) {
    return (values - ... - 2);
}

int main() {
    const int left = subtract_from_twenty(3, 2);  // (20 - 3) - 2
    const int right = subtract_toward_two(20, 3); // 20 - (3 - 2)
    std::cout << "left=" << left << ", right=" << right << '\n';
}
```

先手工展开两三个元素，再选择写法，比只背省略号的位置可靠。浮点加法也可能因分组改变舍入结果，不能随意换方向。

## 四种折叠形式

有了具体结果，再看完整语法。下表假设包中有 `a, b, c`，`init` 是你提供的初值。

| 写法 | 展开结果 | 名称 |
| --- | --- | --- |
| `(... op pack)` | `(a op b) op c` | 一元左折叠 |
| `(pack op ...)` | `a op (b op c)` | 一元右折叠 |
| `(init op ... op pack)` | `((init op a) op b) op c` | 二元左折叠 |
| `(pack op ... op init)` | `a op (b op (c op init))` | 二元右折叠 |

“一元”表示没有额外初值，“二元”表示有初值，并不是参数包只能有一项或两项。最外层括号必不可少；二元折叠两处 `op` 必须是同一个运算符。

## 空包与初值

没有初值时，只有三种运算符允许空包：`&&` 得到 true，`||` 得到 false，逗号得到 `void()`。其他一元折叠在空包时不合法。求和需要零、求积需要一，就显式提供相应初值。

初值还参与类型转换和重载选择。例如字符串拼接可以用 `std::string{}` 作为初值，而不是整数 0。初值的位置也会影响第一步调用哪个运算符。

## 求值顺序和短路

折叠方向描述括号分组，不自动规定每个操作数的求值顺序。规则来自所用运算符：内建 `&&`、`||` 求值时会短路，内建逗号先求左边再求右边，普通算术表达式不能假定按书写顺序求值。重载的逻辑运算符不提供内建运算符的短路效果。

还要区分两个时刻：调用 `all(f(), g())` 时，实参函数调用在进入 `all` 前就已经发生；函数体内的短路不会跳过 `g()`。如果想逐项执行操作并控制顺序，可以对调用本身做逗号折叠：

```text
// 放在接收 Args&&... args 的函数模板内：
(static_cast<void>(process(std::forward<Args>(args))), ...);
```

转为 void 可以确保这里使用内建逗号运算符。每个参数的 `process` 调用按包顺序执行。`forward` 的含义见[完美转发](../cpp11/move-semantics.md#完美转发与引用折叠)。

短路也不意味着模板可以忽略不合法的表达式。形成折叠时，每个操作数都必须有效；要按类型排除无效操作，应结合 [`if constexpr`](control-flow.md) 或约束，而不能把运行时条件当作类型检查。

## 常见误解

- `(args < ...)` 不是“所有参数严格递增”。嵌套比较会把某次比较的 bool 结果用于另一次比较，应另外比较相邻元素。
- `(args + ... + (1 * 2))` 中初值的额外括号有语法意义；复杂包模式或初值应加括号，不能只看运算符优先级猜测。
- 转发引用参数有名字后是左值表达式；需要保留传入方式时使用 `forward`，并避免重复消费同一个对象。

## 深入理解：结果类型和编译成本

折叠展开后仍是普通表达式树。流插入 `(std::cout << ... << values)` 从流开始逐项输出，结果是流引用；内建赋值返回左值；逗号的结果取最后一个表达式。用 `auto` 返回可能丢失引用，需要保留时再考虑 `decltype(auto)`，并核对被引用对象的寿命。

折叠支持规定的一组二元运算符，包括赋值、逗号和成员指针运算符，但不支持条件运算符 `?:`。赋值或成员指针链通常比命名操作更难读，只在确有需要时使用。未展开的参数包只能位于折叠的一侧；多个等长包要先在同一个展开模式中组合。

它减少了递归辅助函数，却仍需要对每一项做类型检查、重载解析。超长参数包会增加表达式深度和代码体积；同质、运行期长度的数据更适合容器循环。复杂操作先提取成命名函数，可以让报错指向具体步骤。

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp17/fold-expressions.md
```

## 权威资料

- [工作草案：折叠表达式语法](https://eel.is/c++draft/expr.prim.fold)

- [N4295：折叠表达式](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2014/n4295.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
