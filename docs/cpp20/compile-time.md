# `consteval`、`constinit` 与扩展 `constexpr`

阅读前建议先了解：[C++11 constexpr](../cpp11/compile-time.md)、[C++14 编译期循环](../cpp14/compile-time.md)。本篇介绍的新增能力属于 C++20；后续版本差异会另行标注。

## 学习目标与三个相似关键字

C++17 的 `constexpr` 函数既可在常量求值中执行，也可退回运行期；它无法表达“这个 API 的普通调用点的立即调用必须产生常量表达式”。静态对象即使希望保持可变，也缺少直接声明“初始化必须属于静态初始化、不能产生初始化顺序风险”的方式。

C++20 加入 `consteval` 和 `constinit`，并继续放宽 `constexpr`。三者分别约束调用时机、初始化阶段和常量求值资格，不能互相替换。

读完后，你应能为编译期解析器选择 `consteval`，为可变全局状态选择性使用 `constinit`，判断 `constexpr` 函数何时仍生成运行时代码，并理解瞬时分配等 C++20 边界。

## 先按需求选择关键字

三者不构成“越来越强”的替代关系：constexpr 让函数可以参与常量求值，consteval 要求普通调用点的立即调用产生常量表达式，constinit 检查静态或线程存储期变量的初始化。

```cpp example id="cpp20-compile-time-basic" std="c++20" file="main.cpp" kind="single" compilers="all" output="constexpr=42, consteval=42, counter=21"
#include <iostream>

constexpr int flexible_twice(int value) { return value * 2; }
consteval int compile_twice(int value) { return value * 2; }
consteval int compile_four_times(int value) {
    return compile_twice(compile_twice(value)); // 立即函数上下文内可以组合
}

constinit int counter = 20; // 启动时完成初始化，之后仍可修改

int main() {
    int input = 21;
    int ordinary = flexible_twice(input);
    constexpr int checked = compile_twice(21);
    static_assert(compile_four_times(10) == 40);
    ++counter;
    std::cout << "constexpr=" << ordinary << ", consteval=" << checked
              << ", counter=" << counter << '\n';
}
```

普通函数也能在运行期计算 ordinary；constexpr 的额外价值是同一个实现也能服务必须常量求值的上下文。consteval 适合源代码中的固定配置验证，不适合读取网络或文件后才知道的输入。constinit 可检查可变全局量的初始化，却不提供 const、线程同步或析构顺序保证；没有全局状态需求时仍优先局部对象。

下面的写法必须被拒绝，不应通过更换编译参数绕过：

```text
int input = 21;
int result = compile_twice(input); // 运行期对象的值不能满足这里的立即调用
constinit constexpr int both = 42; // 两个说明符不能在同一声明中组合
```

语义来源：[立即函数](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1073r3.html)、[constinit 声明](https://eel.is/c++draft/dcl.constinit)。

## 最小语法

```text
consteval int compile_only(int value);       // 每个立即调用必须常量求值
constexpr int compile_or_runtime(int value); // 可用于两种求值环境
constinit int mutable_global = expression;   // 必须静态初始化，仍可修改
```

## 组合示例：立即函数、常量循环与全局初始化

`twice` 强制编译期执行，`sum` 同时适用于编译期和运行期，`runtime_counter` 静态初始化后仍是普通可变整数。

```cpp example id="cpp20-compile-time" std="c++20" file="main.cpp" kind="single" compilers="all" output="42"
#include <array>
#include <iostream>

consteval int twice(int value) {
    return value * 2;
}

constexpr int sum(std::array<int, 3> values) {
    int result = 0;
    for (const int value : values) {
        result += value;
    }
    return result;
}

constinit int runtime_counter = twice(20);

int main() {
    constexpr int offset = sum({0, 1, 1});
    ++runtime_counter;
    std::cout << runtime_counter + offset - 1 << '\n';
}
```

程序输出 `42`。计数器从编译期得到的 `40` 开始，在运行期递增；`offset` 是常量表达式 `2`。`constinit` 不增加 `const`，只在调用本质上必须编译期完成时使用 `consteval`。

## 三个关键字的职责

`constexpr` 变量必须满足相应的常量初始化要求，constexpr 函数则可以参与常量求值。consteval 声明立即函数：不在允许的立即函数上下文中的潜在求值调用是立即调用，必须产生常量表达式。constinit 只适用于静态或线程存储期变量，禁止动态初始化，但不自动增加 const 限定。

立即函数仍有普通函数体语法，却不能像普通运行期函数那样取得可常规调用的函数指针。它适合编译期解析字面量、生成标识和验证配置，失败应产生清晰编译诊断。

`constexpr` 函数可以同时服务编译期和运行期：实参/上下文允许时由常量求值器执行，否则生成普通运行时代码。声明 `constexpr` 不是“编译器一定折叠”的性能命令，只有在需要常量表达式的上下文才强制成功。

潜在求值的 consteval 调用在允许的立即函数上下文之外称为立即调用，必须产生常量表达式；上下文内的组合调用不要求每层形参在定义处都是常量。它仍可接收模板参数并组合其他 constexpr 运算，但不能把运行期输入偷偷带入。立即函数的地址可以在即时函数求值内部使用，却不能作为普通常量表达式结果逃逸成运行期函数指针。

`constinit` 是变量声明说明符，不修饰函数。它要求静态或线程存储期变量具有静态初始化；变量仍可为非 const，类型析构也仍按正常程序退出规则执行。

### 立即函数上下文

立即函数调用若处在另一个立即函数体，或处在标准规定的立即函数上下文中，可以暂时依赖尚未成为具体常量的形参；最终离开该上下文、形成普通潜在求值调用时仍必须完成常量求值。这个规则让 consteval 函数可以互相组合，而不是要求每一层形参在定义处已有值。

立即函数本身隐含 `constexpr` 语义并且也隐含 inline 相关属性，不应再把它理解成一个必须提供单独运行期定义的普通函数。构造函数可以声明为 `consteval`；析构函数、分配函数和释放函数不能使用该说明符，函数也不能同时声明为 `consteval` 与 `constexpr`。

取立即函数地址可以作为即时计算中的中间步骤，例如传给另一个立即算法；但指向立即函数的指针不能作为常量表达式结果逃逸到运行期。该限制保证程序不会在普通执行路径调用一个只定义编译期语义的入口。

### 判断当前求值环境

`std::is_constant_evaluated()` 让同一个 constexpr 函数区分当前是否正在常量求值，可选择适合编译器解释器的算法和运行期优化实现。

```cpp example id="cpp20-is-constant-evaluated" std="c++20" file="main.cpp" kind="single" compilers="all" output="compile=42, runtime=43"
#include <iostream>
#include <type_traits>

constexpr int adjusted(int value) {
    if (std::is_constant_evaluated()) {
        return value * 2;
    }
    return value * 2 + 1;
}

int main() {
    constexpr int compile_time = adjusted(21);
    int input = 21;
    const int run_time = adjusted(input);
    std::cout << "compile=" << compile_time
              << ", runtime=" << run_time << '\n';
}
```

第一次调用初始化 `constexpr` 变量，必须处在常量求值中；第二次实参来自普通对象且结果只初始化普通变量，函数走运行期分支。不要用这种差异改变核心业务语义，否则同一输入在常量求值与普通求值中产生不同结果。常量求值是语言规则，优化器折叠普通求值不会让 is_constant_evaluated() 自动变成 true；它更适合选择等价算法路径。

## 静态初始化顺序

全局对象若需要动态初始化，跨翻译单元依赖可能出现静态初始化顺序问题。`constinit` 强制初始化在动态初始化阶段之前完成，编译器无法证明时直接拒绝。它不解决对象销毁顺序，也不让后续并发修改自动安全。

实现通常把常量初始化结果直接放入数据段，或用零初始化完成初始状态。`runtime_counter` 因此可以在 `main` 前可靠为 40，同时仍允许运行期递增。

静态初始化包括常量初始化和零初始化，先于动态初始化。`constinit` 的价值是把“我认为这是常量初始化”变成编译器检查，而不是靠阅读初始化式推断。若以后某个被调用函数失去 constexpr 能力，声明会立即报错。

同一具有 `constinit` 的变量在其初始化声明和其他声明之间要遵守说明符规则；把带初始化的定义藏在某个源文件、在头文件只给普通声明，可能削弱可诊断性。公共全局量仍应尽量减少。

`thread_local constinit` 能保证每线程对象以静态方式建立初值，但每个线程仍有独立实例。后续写入不需要线程间同步是因为对象不共享，而不是 `constinit` 提供同步。

常量初始化解决的是启动次序，不解决跨翻译单元对象析构次序。全局对象析构若互相访问，仍可能发生生命周期问题；无析构的字面量类型或显式拥有关系更可靠。

`constexpr` 静态数据天然要求常量初始化，所以再写 `constinit constexpr` 是不合法的说明符组合；`constinit` 真正服务的是“初始化必须静态、对象之后仍需可写”的状态。它也可以与 `const` 组合，用于某些不必成为核心常量表达式、但仍要求启动期完成的对象。

具有静态存储期的内联变量在多个翻译单元中仍是一个实体，`constinit` 可确保其初始化类别，却不能修复头文件里不一致的初始化 token 或条件宏造成的 ODR（单一定义规则，约束一个程序中同一实体的多处声明和定义） 问题。编译配置必须让所有定义一致。

## C++20 `constexpr` 扩展

C++20 允许更多对象生命周期操作和标准库函数进入常量求值，包括在受限条件下动态分配，只要分配在常量求值结束前释放。许多容器能力开始逐步 `constexpr` 化，但具体设施仍需查对应标准版本。

编译器的常量求值器会跟踪对象生命周期、越界、未初始化读取和泄漏；一些运行期未定义行为因此可在强制常量上下文提前诊断。

### 瞬时动态分配

C++20 常量求值在受限条件下允许 new-expression 和分配器相关操作，只要分配出的存储在该次常量求值结束前释放。指向编译器常量求值堆的指针不能逃逸进普通程序对象，这常被称为 transient allocation。

这使部分使用动态工作区的算法能够在编译期执行，却不代表 `constexpr std::vector` 可以把运行期堆地址永久写进可执行文件。标准库各容器成员何时被 constexpr 化还要查具体版本。

### 虚函数、联合与生命周期

C++20 放宽了 constexpr 函数体限制，允许更多控制流、对象生命周期操作和在可判定条件下的虚调用。常量求值器知道动态类型时，可以执行符合规则的 constexpr 虚函数；这不是运行期虚表被“搬到编译期”的简单复制。

 placement new 的一般形式、`reinterpret_cast`、I/O、线程同步和系统调用等仍不适合常量表达式。遇到限制应检查真实标准条款，不用宏或未定义行为绕过常量求值器。

析构与构造的 constexpr 支持使更复杂值类型可在编译期管理生命周期。资源必须在求值结束前正确释放，泄漏会让强制常量表达式不成立。

### 常量表达式不是“解释执行所有 C++”

常量求值器执行的是受标准限制的 C++ 子集，并额外拒绝会让核心常量表达式失效的操作。某段代码在运行期测试中从未触发未定义行为，不代表它对所有编译期输入都可求值；常量求值会沿实际选择分支检查，未执行分支通常不因包含运行期操作而自动失败。

抛出表达式可以出现在 constexpr 函数体中，但若实际常量求值路径执行到抛出，结果不能成为常量表达式。由此可以用普通分支表达错误路径，让运行时调用抛异常、编译期调用在强制上下文中产生诊断，不过诊断质量取决于编译器。

常量求值期间产生的对象地址只在相应允许范围内有意义。不能把指向临时求值存储、局部对象或瞬时分配的地址保存进最终静态对象。编译器对“指针逃逸”的拒绝正是为了避免可执行文件携带不存在的编译期地址。

## 立即函数的 API 设计

适合 `consteval` 的输入本质上属于编译配置或源代码常量，例如编译期哈希、格式描述验证、固定字符串解析和单位字面量检查。若调用者合理地需要读取配置文件或网络数据，立即函数会不必要地封死运行期使用。

错误诊断可以通过 `static_assert`、不满足约束或让常量求值失败产生。要让错误靠近调用点，应拆分解析阶段并给约束命名；在深层循环中故意越界只会得到难懂诊断。

立即函数可以调用普通 constexpr 函数，反之普通 constexpr 函数只有在即时函数上下文等规则允许时才能调用 consteval 功能。建立 API 分层时，把可复用纯算法保留为 constexpr，把“必须现在完成”的入口设为 consteval。

## 成本与实践

把计算前移可减少启动工作并验证不变量，但会增加构建时间和模板/常量求值资源。对大表生成测量干净与增量构建，必要时改用生成文件或运行期缓存。

示例用 `consteval` 生成初始值、`constinit` 保证全局初始化，并用更灵活的 `constexpr` 循环求和。选择关键字时先回答：是否必须编译期调用、对象是否必须不可变、还是只需要可靠初始化时机。

编译期计算消耗构建机 CPU 和内存，并可能受到编译器步数、递归深度限制。大型表格若每个翻译单元重复求值，内联变量或预生成源文件可能更合适。把构建时间纳入性能预算。

常量求值还能充当额外验证路径：用 `static_assert` 对边界输入运行算法，同时保留运行期单元测试。两条路径都要测，因为 `is_constant_evaluated`、实现优化和异常替代策略可能不同。

## 三类声明速查

| 关键字/设施 | 关键语义 |
| --- | --- |
| `constexpr` 变量 | const 且必须由常量表达式初始化 |
| `constexpr` 函数 | 可用于编译期，也可在运行期执行 |
| `consteval` 函数 | 允许的立即函数上下文之外，潜在求值调用必须满足立即调用要求 |
| `constinit` 变量 | 静态/线程存储期，不允许动态初始化；可否写入另看 const 限定 |
| `is_constant_evaluated` | 查询当前是否处于常量求值 |
| transient allocation | 编译期分配必须在该次求值结束前释放 |
| constexpr 虚调用 | 动态类型在常量求值中可确定时按规则执行 |
| 编译期抛出路径 | 实际执行 throw 不能形成常量表达式 |
| 地址逃逸 | 编译期临时/分配地址不能进入最终运行期对象 |
| 构建成本 | 常量计算占用编译器 CPU、内存与步数预算 |

## 常量求值专项审查问题

- API 是“可以编译期”还是“必须立即”，关键字是否选对？
- constinit 对象后续可写这一点是否被误解成 const？
- `is_constant_evaluated` 两条路径是否保持相同业务结果？
- 瞬时分配是否在同一次常量求值中全部释放？
- 指针是否指向编译期临时存储并尝试逃逸？
- 实际执行的错误分支是否会 throw 而使常量表达式失败？
- 大型表是否在每个翻译单元重复求值拖慢构建？
- 编译器步数、递归深度和内存限制是否在最低工具链测试？
- 静态初始化问题之外的析构顺序是否仍被单独处理？
- 运行期路径是否也有单元测试，而非只依赖 `static_assert`？

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp20/compile-time.md
```

## 权威资料

- [P1073R3：consteval](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1073r3.html)
- [P1143R2：constinit](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1143r2.html)
- [工作草案：Constant expressions](https://eel.is/c++draft/expr.const)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
