# 返回类型推导与 `decltype(auto)`

C++14 允许普通函数使用 `auto` 推导返回类型。`decltype(auto)` 按 `decltype` 规则保留引用和值类别，适合编写透明包装器。

<!-- example id="cpp14-return-deduction" std="c++14" file="main.cpp" kind="single" compilers="all" output="9" -->
```cpp
#include <iostream>
#include <type_traits>
#include <vector>

auto answer() {
    return 42;
}

template <typename Container>
decltype(auto) first(Container& container) {
    return (container.front());
}

int main() {
    std::vector<int> values{3, 6};
    first(values) = 9;
    static_assert(std::is_same<decltype(first(values)), int&>::value,
                  "decltype(auto) keeps the reference");
    static_assert(std::is_same<decltype(answer()), int>::value,
                  "auto produces a value type");
    std::cout << values.front() << '\n';
}
```

返回类型推导要求同一函数中的所有返回语句推导出一致类型。使用 `decltype(auto)` 时，表达式外是否有括号可能改变结果；不要返回局部变量的引用。

## `auto` 返回值推导

普通函数的 `auto` 返回类型在定义可见时由 `return` 表达式推导，规则类似变量 `auto`：顶层引用和 cv 限定通常被移除。递归函数在第一次递归调用前必须已经出现足以推导返回类型的语句，否则编译器无法确定调用签名。

所有非丢弃 `return` 必须推导为同一类型，不会像条件运算符那样自动寻找公共类型。只有裸 `return;` 的函数推导为 `void`。由于调用方编译时需要看到函数体，返回类型推导不适合隐藏实现的传统二进制接口。

推导类似 `auto variable = expression`：数组和函数通常发生退化，顶层 const 被移除，引用不保留。返回 `const Widget` 表达式通常推导为 `Widget` 值，这符合按值返回的常见语义，却不适合透明代理。

带花括号的初始化列表不能单独为 auto 返回类型提供普通推导目标；`return {1, 2};` 不会自动决定 vector 或 initializer_list。应显式写返回类型或返回一个已命名构造表达式。

虚函数不能只靠推导返回类型定义覆盖契约，因为调用点/基类接口需要稳定签名。协变返回等多态规则仍要求显式类型设计。构造函数和析构函数本来也没有返回类型。

### 递归推导顺序

递归调用只有在函数体前面已经出现可用于推导的 return 后才能形成。把基本情况放在递归调用之前既符合算法结构，也让编译器先确定返回类型。

<!-- example id="cpp14-recursive-return-deduction" std="c++14" file="main.cpp" kind="single" compilers="all" output="factorial=120" -->
```cpp
#include <iostream>

constexpr auto factorial(unsigned value) {
    if (value <= 1) {
        return 1U;
    }
    return value * factorial(value - 1);
}

int main() {
    static_assert(factorial(5) == 120U, "factorial result must be deduced");
    std::cout << "factorial=" << factorial(5) << '\n';
}
```

第一个 return 把结果确定为 unsigned，随后递归表达式也产生 unsigned。若两个分支分别返回 `unsigned` 和 `unsigned long`，即使值都能互转，函数仍因推导类型不一致而不合法。

本例同时显式声明 `constexpr`，所以 `static_assert` 能强制编译期调用。返回类型推导与常量求值是独立特性：删掉 `constexpr` 不影响类型仍推导为 unsigned，但函数不能再用于该常量表达式。

## `decltype(auto)` 的精确传播

`decltype(auto)` 使用整个返回表达式的 `decltype` 结果。返回变量名 `return value;` 得到声明类型，返回 `(value)` 则因为括号表达式是左值而得到引用。它适合转发容器元素或包装另一个 API，却也容易无意返回局部引用。

对于 `operator[]` 等可能返回代理对象的接口，`decltype(auto)` 会原样传播代理类型及生命周期约束；普通 `auto` 可能把它复制为代理，也未必得到业务期望的值类型。透明包装器必须明确是否要保持精确类型，还是要物化为值。

`decltype(auto)` 必须独占声明的类型说明部分，不能写成 `const decltype(auto)`、`decltype(auto)&` 等组合。cv/ref 信息来自初始化或返回表达式本身。需要强制额外限定时应使用显式尾置返回类型。

函数调用表达式若返回 `T&&`，decltype(auto) 会继续返回 `T&&`；返回 `T&` 则保留左值引用；返回纯右值则得到 T。它适合 forwarding wrapper，但包装器还必须用 forward 保留参数值类别，仅保留结果类型并不足够。

成员访问也有未加括号 id/member access 的特殊 decltype 规则。`return object.member;` 可能得到成员声明类型，而 `return (object.member);` 按表达式值类别得到引用。代码评审不能只看“看起来都返回成员”。

### 临时对象与代理

返回临时对象的子对象引用会悬空。即使底层函数返回一个值对象，包装器写 `return (make_object().member);` 也可能把临时成员的 xvalue 引用暴露到完整表达式之后。

`vector<bool>::reference` 一类代理不是 bool&。decltype(auto) 会精确保留代理返回，调用方可能在容器重分配后持有失效代理。若 API 语义是取得布尔快照，应显式返回 bool，而不是追求“零复制”。

透明性是契约而非永远正确的优化。视图/迭代器适配层常需要保持引用，业务服务边界通常更适合拥有值。

## ABI、生命周期与性能

推导发生在编译期，不引入运行时标签。保留引用可以避免复制，但把被包装对象的生命周期和别名暴露给调用方；返回值则更安全地拥有结果，并可利用复制消除和移动。

公开库中若返回类型是实现细节，改变函数体可能改变推导类型并破坏调用方重新编译或 ABI 假设。稳定接口宜显式写返回类型，局部泛型辅助函数更适合推导。

使用推导返回类型的函数模板定义必须对实例化点可见，通常放在头文件。普通非模板函数虽然可以先声明再定义，但调用在返回类型推导完成前受到限制；跨源文件仅写 `auto f();` 不能像明确返回类型声明那样供调用方独立编译。

改变实现从 `return value;` 到 `return (value);` 对 decltype(auto) 是 API 级变化：从值变成引用，影响 mangling/调用约定、生命周期和可修改性。即便源码调用仍能编译，也可能出现二进制不兼容或悬空。

按值推导通常可利用移动和复制消除。为了少一次复制而改成引用返回，必须证明所有者寿命，而不能只依据微基准。小对象值返回往往更容易优化且更安全。

## 与尾置返回类型的选择

C++11 的 `auto f(args) -> decltype(expression)` 在函数体之前就给出返回类型，适合 SFINAE 和递归声明；C++14 的纯 auto 写法更短，但需要实例化函数体才能完成推导。

需要让非法操作从重载集中移除时，尾置 decltype 往往比函数体 auto 推导更可靠。需要可读稳定契约时直接写具体类型。只有结果类型明显跟随实现且函数局部/模板化时，才优先纯推导。

decltype(auto) 主要用于“与这个表达式完全相同”的适配器。若设计文档无法一句话说明为何必须保留引用和值类别，普通 auto 或显式类型通常更合适。

## 示例解析与检查清单

主示例中 `first` 返回带括号的 `front()` 左值，因此调用结果是 `int&`，赋值直接修改容器。检查每个 `decltype(auto)` 返回路径的值类别、被引用对象寿命和代理语义；若不需要透明转发，优先用明确返回类型。

## 括号如何改变返回类型

对于未加括号的变量名，`decltype(name)` 得到变量声明类型；`decltype((name))` 把括号中的名字视为普通左值表达式，得到左值引用。`decltype(auto)` 原样采用这套规则，因此 `return value;` 与 `return (value);` 可能分别返回值和引用。

<!-- example id="cpp14-decltype-auto-parentheses" std="c++14" file="main.cpp" kind="single" compilers="all" output="global=7, copy=9" -->
```cpp
#include <iostream>

int global_value = 1;

decltype(auto) reference_to_global() {
    return (global_value);
}

auto copy_of_global() {
    return global_value;
}

int main() {
    reference_to_global() = 7;
    int copy = copy_of_global();
    copy = 9;
    std::cout << "global=" << global_value << ", copy=" << copy << '\n';
}
```

如果把局部变量写成带括号返回，函数会返回悬空引用。代码评审应把每个 `decltype(auto)` 返回表达式的存储来源明确写出来：全局对象、参数、成员、容器元素还是临时对象。

## 多分支推导

`auto` 或 `decltype(auto)` 返回函数的所有非丢弃 return 必须推导为相同类型。编译器不会自动寻找共同基类，也不会在值与引用之间选择更安全的形式。条件分支需要不同具体类型时，C++14 应显式设计统一返回类型、使用多态，或在后续标准中采用 `variant`。

模板中的 `if` 两个分支在 C++14 都参与返回类型推导；还没有 `if constexpr` 丢弃不适用分支。按类型选择不同返回表达式通常要使用重载、标签分派或专门化，而不是普通 `if (type_trait<T>::value)`。

返回 `T&` 与 `const T&` 不一致，返回 `T` 与 `T&&` 对 decltype(auto) 也不一致。为了让编译通过而对某个分支强制转换，必须确认转换不会制造临时引用或切片。

## 推导与声明可见性的补充

### 语法结果速查

| return 形式 | 典型推导结果 |
| --- | --- |
| `auto f(){ return value; }` | 按值，类似 auto 变量推导 |
| `decltype(auto) f(){ return value; }` | 未加括号 id-expression 走 decltype 特例 |
| `decltype(auto) f(){ return (value); }` | 左值通常推导为引用，需证明寿命 |
| `return std::move(local)` + auto | 按值结果可移动构造 |
| `return std::move(local)` + decltype(auto) | 可能返回悬空 `T&&` |
| 多个 return + auto | 每个推导类型必须相同，不自动求共同类型 |
| 空 `return;` | 对应 void 推导路径 |
| 递归 return | 在递归调用前必须已有可确定返回类型的路径 |
| 仅有 `auto f();` 声明 | 使用点不能在未知定义下完成返回推导 |
| 尾置 `decltype(expr)` | 可把表达式有效性放入声明/SFINAE 语境 |

普通 `auto` 返回按值推导，通常丢弃顶层 cv/引用并让数组、函数表达式退化；`decltype(auto)` 才按 decltype 规则精确保留。返回引用不是优化开关，而是生命周期契约。

只有 `auto f();` 声明而看不到定义时，调用方无法获知推导类型并正常使用函数。返回类型推导不适合用作跨源文件隐藏返回类型的 ABI 技巧，定义通常必须在首次需要推导的地方可见。

递归调用出现在任何可用于确定返回类型的 return 之前时，编译器尚不知道递归表达式类型。简单递归可先出现基例，但互递归和公共接口应写显式返回类型。

`return std::move(local);` 配合 decltype(auto) 会产生指向局部对象的右值引用并立即悬空。要移动出局部对象，应按值返回，让移动或复制消除建立独立结果对象。

成员访问还有 decltype 特例：`decltype(object.member)` 取成员声明类型，`decltype((object.member))` 按表达式类别常得到引用。透明访问器应以 static_assert 固定预期返回类型。

## 返回推导专项审查

- auto 按值是否正是接口需要而非意外复制？
- decltype(auto) 返回引用的目标是否持续存活？
- return 括号是否改变 decltype 推导类别？
- 多分支返回是否推导完全相同类型？
- 递归调用前是否已有可确定返回类型？
- 仅声明未知 auto 返回是否被跨源文件调用？
- 代理对象是否应该物化为稳定 value_type？
- 是否用 std::move(local) 产生悬空 T&&？
- SFINAE 是否应该放在尾置返回声明而非函数体？
- 公共 ABI 是否更适合显式返回类型？

## 权威资料

- [N3638：返回类型推导](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3638.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
