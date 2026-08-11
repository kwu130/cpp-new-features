# 模板参数与属性

C++17 允许 `auto` 非类型模板参数，并标准化了 `[[nodiscard]]`、`[[maybe_unused]]` 和 `[[fallthrough]]` 等常用属性。

<!-- example id="cpp17-templates-attributes" std="c++17" file="main.cpp" kind="single" compilers="all" output="medium" -->
```cpp
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

属性主要表达意图和触发诊断，不应依赖编译器忽略返回值警告来保证业务正确性。非类型模板参数仍受允许类型范围约束，这一范围在 C++20 中继续扩大。

## `auto` 非类型模板参数

非类型模板参数把一个编译期值纳入类型身份。C++14 以前必须先写明值的类型，C++17 的 `template<auto Value>` 让编译器从实参推导类型。`twice<21>` 中参数类型是 `int`，而 `twice<21L>` 会形成不同模板实例。

允许的值仍受非类型模板参数规则限制，主要覆盖整数、枚举、指针等当时可表示的结构。值必须是合适的常量表达式。因为值参与符号和类型身份，大量不同取值会产生大量实例，增加编译与代码尺寸成本。

推导遵循模板实参的类型规则，而不是先统一转成某个最大整数类型。`value<1>`、`value<1L>` 和 `value<'\1'>` 的参数类型不同，因而可以选择不同特化或重载。`decltype(Value)` 能在模板体内取得被推导的确切类型。

<!-- example id="cpp17-auto-nttp-types" std="c++17" file="main.cpp" kind="single" compilers="all" output="int=42, char=A" -->
```cpp
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

## 属性与工具链策略

属性诊断不是运行时契约。构建系统应统一警告级别并把关键警告纳入 CI，但库 API 的正确性仍要由类型、所有权和测试保证。调用方可以关闭警告，编译器也可能选择不同诊断文本。

公共头文件使用标准属性通常比编译器专用宏更可移植；若要兼容 C++17 之前版本，可用 `__has_cpp_attribute` 等条件探测封装。条件宏必须保证所有翻译单元看到一致声明，避免制造 ODR 或 ABI 差异。

## 底层与性能

`nodiscard` 和 `maybe_unused` 通常只影响前端诊断，不生成运行时代码。`fallthrough` 也主要消除警告，实际控制流仍是普通贯穿。不要把属性当作安全机制；API 仍需通过类型和控制流保证正确。

## 示例解析与工程实践

示例用值模板生成常量，用 `nodiscard` 标记必须处理的分类结果，并显式声明 switch 贯穿。库作者应把 `nodiscard` 用在错误码、资源句柄和纯计算结果上，但避免为所有函数机械添加导致警告疲劳；使用方不应通过无意义强制转换掩盖真正遗漏。

## 权威资料

- [P0127R2：auto 非类型模板参数](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0127r2.html)
- [工作草案：attributes](https://eel.is/c++draft/dcl.attr.grammar)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
