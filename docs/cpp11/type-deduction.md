# 类型推导：`auto` 与 `decltype`

## 为什么需要

模板和迭代器类型往往很长。`auto` 根据初始化表达式推导变量类型，`decltype` 则在不求值表达式的情况下取得其类型，使代码既简洁又保持静态类型检查。

## 核心语义

- `auto` 的规则与模板实参推导接近，通常会丢弃顶层 `const` 和引用；需要引用时应显式写 `auto&` 或 `const auto&`。
- `decltype(name)` 对未加括号的变量名给出声明类型。
- `decltype((expression))` 根据表达式值类别可能得到引用类型。

<!-- example id="cpp11-type-deduction" std="c++11" file="main.cpp" kind="single" compilers="all" output="6" -->
```cpp
#include <iostream>
#include <type_traits>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3};
    auto iterator = values.begin();
    const auto& first = values.front();

    int number = 6;
    decltype(number) copy = number;
    static_assert(std::is_same<decltype((number)), int&>::value,
                  "a parenthesized lvalue produces a reference");
    static_assert(std::is_same<decltype(first), const int&>::value,
                  "the explicit reference is retained");

    std::cout << (*iterator + copy - first) << '\n';
}
```

## 实践建议

当类型由右侧表达式自然决定时使用 `auto`；当具体类型本身表达业务含义时保留显式类型。遍历容器中的大型对象时优先使用 `const auto&`，避免无意复制。

## 易错点

`auto value = {1, 2, 3};` 推导为 `std::initializer_list<int>`，并非普通整数。不要仅为缩短一个清晰的基础类型而滥用 `auto`。

## 学习目标

读完本章后，应能判断 `auto` 是否保留 `const`、引用和数组属性，能解释 `decltype(x)` 与 `decltype((x))` 的差别，并能在泛型代码中选择值、左值引用或转发引用。

## 推导规则拆解

把 `auto` 想象成模板形参 `T` 很有帮助。对于 `auto value = expression`，编译器近似执行按值形参推导，因此顶层 `const` 和引用被去掉；表达式指向对象的底层 `const` 仍然保留。对于 `auto&`，引用本身不会成为对象类型的一部分，但被引用对象的 cv 限定会保留。

| 声明 | 初始化表达式类型 | 推导结果 |
| --- | --- | --- |
| `auto x = const_int` | `const int` 左值 | `int` |
| `const auto& x = value` | `int` 左值 | `const int&` |
| `auto* x = pointer` | `const int*` | `const int*` |
| `auto&& x = lvalue` | `int` 左值 | `int&`（引用折叠后） |
| `auto&& x = temporary` | `int` 右值 | `int&&` |

`decltype` 不执行模板式推导。若操作数是未加括号的名字或成员访问，它直接返回该实体的声明类型；其他表达式则按值类别决定结果：纯右值得到 `T`，将亡值得到 `T&&`，左值得到 `T&`。因此多一层括号可能改变 API 的返回类型。

### 顶层与底层 const

按值 auto 丢弃的是对象本身的顶层 const；指针指向对象的 const 属于底层限定并保留。`const int* p` 推导 `auto q=p` 得到 `const int*`，而 `int* const p` 的顶层指针 const 会从 q 类型移除。

auto&/auto* 模式把限定分布写进声明：`const auto&` 无论实参是否 const 都建立只读引用，`auto&` 从 const 左值推导出 const T&，不会绕过 const。`auto*` 只接受可推导指针形态。

`auto&&` 只有在 auto/T 由当前初始化推导时体现转发引用折叠；已经固定别名或类模板参数中的 `T&&` 是普通右值引用。不要看到两个 `&` 就一概称完美转发。

### 初始化列表的特殊推导

用等号花括号初始化 auto 时，编译器尝试推导 `initializer_list<U>`，所有元素必须给出一致 U；不会为 int/double 自动找 common_type。直接列表 auto 的细节经历标准缺陷修正，跨版本代码宜显式写目标类型。

函数模板形参 `template<class T> f(T)` 不能从裸 `{1,2}` 推导 T，除非形参本身是 initializer_list<T> 等能接收列表的已知模式。auto 变量的特殊规则不能泛化到所有模板推导。

## 编译器视角与成本

类型推导完全发生在编译期。编译器在语义分析阶段确定具体类型，之后生成的代码与手写该类型通常没有区别；`auto` 不是 JavaScript 式动态类型，也不会在对象里保存运行期类型标签。

推导后的类型仍参与重载解析、模板实例化和生命周期规则。若推导结果发生变化，源代码虽然仍写着 `auto`，ABI、重载选择或复制成本却可能改变，所以公共接口返回类型的变更仍应按接口变更审查。

局部 auto 会隐藏类型拼写但不隐藏语义。初始化函数从 iterator 改成 const_iterator、从值改成代理后，后续重载和赋值行为可能变化；编译器能保证类型正确，不能保证业务仍正确。

调试信息仍可包含推导后的具体类型，错误消息也会展示模板实例。编译时间不会因为少写字符自动降低；复杂初始化表达式仍需完整推导和重载解析。

公共类数据成员在 C++11 不能用普通非静态 `auto member = ...` 省略类型，函数参数也不能写泛型 auto（C++14 Lambda/C++20 abbreviated template 才扩展）。C++11 auto 主要用于变量声明和尾置返回占位语法。

## 示例解析

主示例中的迭代器类型由 `values.begin()` 决定。`first` 显式写成 `const auto&`，既不复制元素又阻止修改。两个 `static_assert` 分别验证括号表达式产生左值引用，以及显式引用声明保留底层常量性。

## 常见错误

- 使用 `auto item` 遍历大型对象会逐项复制。
- `std::vector<bool>` 的元素是代理对象；`auto value = bits[0]` 未必得到 `bool`。
- 数组按值推导会退化为指针，使用 `auto&` 才能保留数组类型和长度。
- 从函数返回的代理类型使用 `auto` 保存，可能让临时依赖对象提前失效。

`auto` 按值接收引用返回会复制被引用对象，这有时是想要快照，有时是隐藏性能 bug。若 API 返回锁保护对象引用，复制后锁生命周期与复制成本也要审查。

`const auto value = expression` 重新给推导值加顶层 const，但现代返回值优化/移动场景中局部 const 可能阻止后续 move。只在确需不可修改时加 const，不把它当默认装饰。

用 auto 保存 `{}` 空列表无法推导元素类型。写 `std::initializer_list<int> values{}` 或目标容器类型，避免依赖上下文不存在的类型信息。

## 工程检查清单

先问“这里需要值还是引用”，再决定是否写 `&`；确认生命周期比引用长；对可能是代理对象的表达式查阅返回类型；在模板边界用 `static_assert` 或类型萃取验证关键推导结论。

## 数组、函数与代理类型

按值推导会执行数组到指针、函数到函数指针的退化。引用形式不会退化，所以泛型函数可以通过数组引用保留长度。这个差异不仅影响类型名称，还决定 `sizeof`、重载和模板参数能否看到原始边界。

`decltype` 不会执行数组退化：对数组变量名使用 `decltype` 得到完整数组类型。对函数名使用 `decltype` 得到函数类型，而不是函数指针。需要声明“与表达式完全一致”的中间类型时，它比 `auto` 更精确。

标准库中的代理引用是另一个高风险区域。`vector<bool>::reference`、某些迭代器解引用结果和表达式模板对象看起来像普通值，却可能只保存对底层对象的间接访问。使用 `auto` 会保存代理本身；若要立即取得业务值，应显式写目标类型。

函数类型按值 auto 退化为函数指针，auto& 保留函数左值引用；decltype(function_name) 得到函数类型，不能直接定义该类型的对象但可用于指针/引用声明。回调适配代码要区分函数、函数指针和函数对象。

字符串字面量是 const char[N] 左值：auto 得 const char*，auto& 保留数组界。需要精确字节长度（含结尾零）时引用/模板数组参数可读取 N；一旦退化只能重新扫描或另传长度。

表达式模板代理可能引用多个操作数并延迟计算。保存 auto proxy 后让操作数离开作用域会悬空；显式目标矩阵/数值类型可迫使立即物化。是否代理必须查库契约。

## `decltype` 的未求值语境

decltype 操作数通常不求值，所以可写 `decltype(f(std::declval<T>()))` 查询调用结果而不实际调用，也不要求有运行期对象。语法和重载解析仍会检查，表达式必须可形成。

未求值不代表可随便解引用无效指针来执行；这里只构造类型表达式。`decltype(*pointer)` 按左值规则得到 T&，不会在运行期读取地址。

C++11 常用尾置返回 `auto function(args) -> decltype(expression)`，因为参数名在箭头处已进入作用域，能表达依赖参数的结果类型。C++14 才允许普通函数体 auto 返回推导，decltype(auto) 也属后续特性。

<!-- example id="cpp11-auto-decltype-arrays" std="c++11" file="main.cpp" kind="single" compilers="all" output="length=3, first=9" -->
```cpp
#include <cstddef>
#include <iostream>
#include <type_traits>

template <std::size_t Size>
std::size_t array_length(const int (&)[Size]) {
    return Size;
}

int main() {
    int values[3] = {1, 2, 3};
    auto pointer = values;
    auto& array = values;
    decltype((values[0])) first = values[0];
    first = 9;

    static_assert(std::is_same<decltype(pointer), int*>::value,
                  "by-value auto decays an array");
    static_assert(std::is_same<decltype(array), int (&)[3]>::value,
                  "auto reference keeps the bound");
    std::cout << "length=" << array_length(array)
              << ", first=" << values[0] << '\n';
}
```

## 选择 `auto` 还是 `decltype`

局部变量由初始化表达式自然决定且不关心精确引用属性时使用 `auto`。需要复制表达式的声明类型、编写尾置返回类型或验证值类别时使用 `decltype`。若接口必须稳定，显式业务类型通常比两者都更容易审查。

## 推导规则速查

| 写法 | 结果/边界 |
| --- | --- |
| `auto x = expr` | 类似按值模板推导，通常丢顶层 const 和引用 |
| `auto& x = expr` | 必须绑定左值并保留底层 cv |
| `const auto& x = expr` | 可绑定临时并把其寿命延长到引用作用域 |
| `auto&& x = expr` | 变量声明中按转发引用规则折叠 |
| `auto x{1}` | C++11 与初始化列表推导规则相关，跨版本需测试 |
| `decltype(name)` | 未加括号 id-expression 取实体声明类型 |
| `decltype((name))` | 按表达式值类别，左值通常得到 `T&` |
| `decltype(prvalue)` | 得到非引用 T |
| `decltype(xvalue)` | 得到 `T&&` |
| `decltype(expr)` | 未求值，不执行 expr 的运行期副作用 |

## 类型推导专项审查

- auto 是否丢失了 API 本应保留的引用或顶层 const？
- `auto&&` 是转发引用还是非推导语境普通右值引用？
- 花括号初始化是否具有可推导的 initializer_list 入口？
- decltype 的未加括号名称特例是否符合预期？
- 额外括号是否把返回/变量类型改变为引用？
- 数组是否被 auto 按值退化成指针？
- 代理类型是否被 auto 保存而非物化 value_type？
- 未求值 decltype 中名称是否仍需可访问且语法合法？
- 跨版本 auto 花括号细节是否在最低标准编译？
- 是否用 static_assert 锁定关键推导结果？

## 权威资料

- [自动类型推导与占位类型](https://eel.is/c++draft/dcl.spec.auto)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
