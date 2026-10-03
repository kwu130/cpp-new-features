# 模板参数与属性

阅读前建议先了解：[普通模板](../prerequisites.md#普通模板与类型推导)、[编译期常量](../cpp11/compile-time.md)；属性可以独立学习。本篇介绍的新增能力属于 C++17；后续版本差异会另行标注。

## 学习目标与本篇范围

C++14 的非类型模板参数必须先写明值类型，例如 `template<int Value>`；同一模板若希望接受不同整数或枚举类型，需要额外模板层。另一方面，编译器长期用各自扩展表达“返回值不应忽略”“变量可能未使用”和“这里有意贯穿 case”，可移植诊断能力有限。

C++17 允许用 `auto` 推导非类型模板参数的类型，并加入 `[[nodiscard]]`、`[[maybe_unused]]`、`[[fallthrough]]` 三项常用标准属性。本篇把它们放在一起讲，是因为它们都增强声明的表达力，但二者机制不同：模板值影响实例身份，属性主要向实现和读者传达意图。

读完后，你应能判断模板值的实际类型与实例数量，正确放置三项属性，并理解警告、程序正确性和 ABI（二进制接口约定，例如调用方式与对象布局） 之间的边界。

## 最小语法

```text
template <auto Value>
struct constant { /* decltype(Value) 是推导后的类型 */ };

[[nodiscard]] Result open_resource();
[[maybe_unused]] const auto trace = build_trace();

case first:
    prepare();
    [[fallthrough]];
case second:
    execute();
```

## 模板值与诊断属性分开理解

以下片段只对比写法；完整、可运行的程序见后文。

```text
// 传统固定整数类型
template <int Value> struct OldConstant;
// C++17：值与它的类型共同决定特化
template <auto Value> struct Constant;
// 返回值需要调用者检查时表达意图
[[nodiscard]] Result open_resource();
```

auto 模板值适合本来就需要接受不同整数或枚举类型的接口；需要固定 size_t 尺寸时仍可明确声明。属性用来表达诊断意图，不是运行期检查：忽略 nodiscard 结果通常产生警告，而不是由语言保证编译失败。后面的例子分别解释 fallthrough 和 maybe_unused。

## 第一个完整示例

示例用 `twice<21>` 展示自动推导的值参数，并在一个 `switch` 中演示三项属性各自的出现位置。

```cpp example id="cpp17-templates-attributes" std="c++17" file="main.cpp" kind="single" compilers="all" output="medium"
#include <iostream>
#include <string>

template <auto Value>
constexpr auto twice = Value * 2;

[[nodiscard]] int classify(int value) {
    return value < 10 ? 1 : 2;
}

int main() {
    [[maybe_unused]] constexpr auto answer = twice<21>;
    switch (classify(12)) {
    case 1:
        std::cout << "small\n";
        break;
    case 2:
        std::cout << "medium";
        [[fallthrough]];
    default:
        std::cout << '\n';
    }
}
```

程序输出 `medium`。模板实参 `21` 的类型推导为 `int`；`answer` 声明为 constexpr 变量，因此其类型为 `const int`；`classify` 的返回值被实际检查；`fallthrough` 明确表示从 `case 2` 继续执行 `default` 不是遗漏 `break`。属性主要表达意图和触发诊断，非类型模板参数则仍受 C++17 允许类型范围约束。

## `auto` 非类型模板参数

非类型模板参数把一个编译期值纳入类型身份。C++14 以前必须先写明值的类型，C++17 的 `template<auto Value>` 让编译器从实参推导类型。`twice<21>` 中参数类型是 `int`，而 `twice<21L>` 会形成不同模板实例。

允许的值仍受非类型模板参数规则限制，主要覆盖整数、枚举、指针等当时可表示的结构。值必须是合适的常量表达式。因为值参与符号和类型身份，大量不同取值会产生大量实例，增加编译与代码尺寸成本。

推导遵循模板实参的类型规则，而不是先统一转成某个最大整数类型。`value<1>`、`value<1L>` 和 `value<'\1'>` 的参数类型不同，因而可以选择不同特化或重载。`decltype(Value)` 能在模板体内取得被推导的确切类型。

```cpp example id="cpp17-auto-nttp-types" std="c++17" file="main.cpp" kind="single" compilers="all" output="int=42, char=A"
#include <iostream>
#include <type_traits>

template <auto Value>
struct Constant {
    using value_type = decltype(Value);
    static constexpr auto value = Value;
};

int main() {
    using Answer = Constant<42>;
    using Letter = Constant<'A'>;
    static_assert(std::is_same_v<Answer::value_type, int>);
    static_assert(std::is_same_v<Letter::value_type, char>);
    std::cout << "int=" << Answer::value << ", char=" << Letter::value << '\n';
}
```

同一个模板由实参同时确定值和类型，适合寄存器编号、枚举策略、固定维度等编译期领域值。若 API 实际要求所有值都属于某个统一类型，显式写 `template<std::size_t N>` 更能表达约束，也能避免有符号/无符号实例意外分裂。

### 可接受值与身份

C++17 的非类型模板参数类型集合仍较受限：整数和枚举、对象/函数指针、左值引用、成员指针以及 `nullptr_t` 等是主要类别，浮点数和任意类对象不能直接作为值参数。后续标准扩大了结构化类型范围，但不能反推到 C++17。

指针或引用实参必须满足模板实参的常量表达式及链接/身份约束，不能随意把字符串字面量、临时对象或子对象地址当作稳定模板身份。把地址编码进类型会强烈耦合实体链接属性，普通运行期指针参数往往更合适。

`template<auto... Values>` 可以形成异构值包，每个元素分别推导类型。若算法要求所有值同类型，需要显式断言，或使用先声明类型再接值包的传统形式。异构能力很强，但也会让错误信息和重载集合更复杂。

### `decltype(auto)` 形式的值参数

C++17 还允许把占位类型写成 `template<decltype(auto) Value>`。它按 `decltype` 规则推导，可在允许的非类型模板参数范围内保留引用性质；`template<auto>` 则按普通 auto 推导更倾向得到值类型。这个能力很少需要，且更容易把实体身份和链接要求暴露到公共类型中，应只在确实需要引用语义的元编程接口使用。

占位类型还可以带约束前的类型修饰组合，但最终推导类型必须仍属于 C++17 允许的非类型模板参数类型。`auto` 并没有绕过常量表达式、地址身份或可表示类型的规则，只省略了参数声明中的显式类型。

### 模板实例化与 ABI

每个“类型 + 值”组合是不同特化，通常也会形成不同符号。把用户输入或大范围业务编号直接提升为模板值会造成实例化爆炸、目标文件增大和增量编译变慢。值只影响少量分支时，运行期参数或普通 `constexpr` 参数常更经济。

公共库把 `auto` NTTP 暴露在导出类型中时，调用方编译器必须对实参类型和修饰得出一致结论。`1` 与平台相关宽度类型、字符类型或枚举值的差异会进入 ABI 名字；接口应使用领域枚举或显式类型包装收窄变化空间。

## 标准属性的语义边界

属性为实现提供结构化元信息。编译器必须识别标准属性的语法，但多数属性影响诊断或优化提示，不改变程序核心语义。

- `[[nodiscard]]` 提醒调用方不要丢弃重要结果；是否诊断及诊断级别由实现决定。
- `[[maybe_unused]]` 抑制有意未使用实体的警告，适合平台条件编译和断言只在调试构建存在的变量。
- `[[fallthrough]]` 只能放在 switch 分支末尾附近，声明落入下一分支是有意行为。

属性放置位置决定它修饰声明、类型还是语句。随意移动可能改变含义或不再合法，应靠近意图对象。

标准属性使用双中括号语法，可以携带属性命名空间和参数。实现遇到它不认识的属性通常应忽略而不是把语法误当成宏；但标准属性若用在不允许的位置，程序仍可能不合法。`__attribute__`、`__declspec` 等是实现扩展，不具备相同可移植性。

### `nodiscard`

C++17 的 `[[nodiscard]]` 可标记函数等规定实体。调用返回值作为 discarded-value expression 时，编译器被鼓励给出警告。显式转换为 `void` 通常表达有意丢弃，但这只是抑制诊断，不执行额外检查。

它适合错误状态、必须释放/检查的句柄包装结果和不会产生其他副作用的纯查询。对每个 getter 都标记可能造成警告疲劳，使真正关键结果被忽略。C++20 才加入属性中的诊断字符串，不应在 C++17 文档示例中使用 `[[nodiscard("reason")]]`。

### `maybe_unused`

该属性可用于有意可能未使用的类、变量、函数、枚举、结构化绑定等受支持实体。典型场景是只在 `assert` 启用时使用的变量，或因平台条件分支而暂时不用的参数。它不应该掩盖本可删除的死代码，也不会让对象构造或析构消失。

### `fallthrough`

`[[fallthrough]];` 是空语句形式，只能出现在 `switch` 中，且下一条要执行的语句属于后续 case/default 标签。它不改变跳转；若前一分支执行 `break`、`return` 或抛异常，属性就没有表达必要。把业务逻辑依赖的贯穿写清楚，并避免跨越需要独立初始化的作用域。

### 属性出现位置与重复声明

声明语法中可能有多个可放属性的位置，但含义不一定相同：放在声明说明符附近可能应用到实体，放在类型构造部分可能尝试应用到类型。标准属性各自规定可作用的实体集合；编译器接受某个扩展位置不代表另一工具链也接受。公共头文件应采用标准明确列出的放置方式。

同一函数的多次声明若属性不一致，会造成诊断表现和接口可读性混乱；某些属性还有“首次声明”或声明一致性相关要求。把属性放进唯一公共声明，再让定义包含该声明，是比在实现文件补标更可靠的做法。

`[[maybe_unused]]` 抑制的是未使用诊断，不改变 ODR（单一定义规则，约束一个程序中同一实体的多处声明和定义）-use、初始化和析构。带副作用的局部对象即使标记该属性仍会照常构造；它不能作为条件编译或删除代码的工具。

### `__has_cpp_attribute` 探测

预处理表达式 `__has_cpp_attribute(attribute-token)` 可查询实现报告的属性支持版本，适合需要兼容旧语言模式的头文件。返回非零表示实现识别相应属性，但不保证项目警告配置一定产生诊断，也不替代对合法出现位置的检查。

探测编译器专属属性时要使用命名空间限定 token，并提供完全为空的回退宏。宏封装应只解决语法兼容，不应让不同翻译单元因构建宏不同而看到实质不同的类布局或函数类型。

## 属性与工具链策略

属性诊断不是运行时契约。构建系统应统一警告级别并把关键警告纳入 CI，但库 API 的正确性仍要由类型、所有权和测试保证。调用方可以关闭警告，编译器也可能选择不同诊断文本。

公共头文件使用标准属性通常比编译器专用宏更可移植；若要兼容 C++17 之前版本，可用 `__has_cpp_attribute` 等条件探测封装。条件宏必须保证所有翻译单元看到一致声明，避免制造 ODR 或 ABI 差异。

## 底层与性能

`nodiscard` 和 `maybe_unused` 通常只影响前端诊断，不生成运行时代码。`fallthrough` 也主要消除警告，实际控制流仍是普通贯穿。不要把属性当作安全机制；API 仍需通过类型和控制流保证正确。

## 示例解析与工程实践

示例用值模板生成常量，用 `nodiscard` 标记必须处理的分类结果，并显式声明 switch 贯穿。库作者应把 `nodiscard` 用在错误码、资源句柄和纯计算结果上，但避免为所有函数机械添加导致警告疲劳；使用方不应通过无意义强制转换掩盖真正遗漏。

## 模板值与属性速查

| 语法 | 关键语义 |
| --- | --- |
| `template<auto V>` | 从模板实参同时推导值和类型 |
| `V=1` 与 `V=1L` | 类型不同，形成不同特化 |
| `template<auto... Vs>` | 可形成异构值包 |
| `decltype(V)` | 取得推导后的确切非类型参数类型 |
| C++17 NTTP 类型 | 仍限整数、枚举、指针/引用等规定类别 |
| `[[nodiscard]]` | 鼓励诊断丢弃结果，不强制运行期处理 |
| `[[maybe_unused]]` | 抑制有意未使用诊断，不删除初始化副作用 |
| `[[fallthrough]];` | 声明 switch 贯穿意图，不改变控制流 |
| 属性位置 | 决定修饰实体/类型/语句，不能任意移动 |
| `__has_cpp_attribute` | 探测语法支持，不保证警告策略 |

## 模板值与属性专项审查问题

- `1`、`1L` 等不同值类型是否意外分裂模板实例？
- auto NTTP 最终类型是否属于 C++17 允许集合？
- 指针/引用实参是否满足稳定实体和常量表达式要求？
- 异构值包是否其实应约束成统一类型？
- 大量业务编号是否被不必要提升为模板值造成膨胀？
- nodiscard 是否只用于真正必须处理的结果？
- 调用者显式丢弃结果是否有清晰理由？
- `maybe_unused` 是否掩盖本可删除的死代码？
- fallthrough 是否紧邻真实下一 case 且没有 break？
- 属性是否放在标准允许且所有工具链一致的位置？

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp17/templates-and-attributes.md
```

## 权威资料

- [P0127R2：auto 非类型模板参数](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0127r2.html)
- [工作草案：attributes](https://eel.is/c++draft/dcl.attr.grammar)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
