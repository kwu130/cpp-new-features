# Concepts 与约束

Concepts 为模板参数声明可读、可组合的约束，让重载选择更明确，也能把模板错误定位到接口边界。

<!-- example id="cpp20-concepts" std="c++20" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <concepts>
#include <iostream>

template <typename T>
concept Arithmetic = std::integral<T> || std::floating_point<T>;

template <Arithmetic T>
T twice(T value) {
    return value + value;
}

template <typename T>
requires std::integral<T> && (sizeof(T) >= 4)
T add(T left, T right) {
    return left + right;
}

int main() {
    static_assert(Arithmetic<double>);
    std::cout << add(twice(10), 22) << '\n';
}
```

Concept 应描述调用者真正依赖的语义能力，而不是只罗列碰巧使用的具体类型。优先复用标准 Concept，并把复杂约束拆成有业务含义的命名 Concept。

## 从 SFINAE 到约束系统

C++20 之前常把 `enable_if` 放进返回类型或模板参数，通过替换失败移除候选。这能工作，但接口难读，失败位置可能深入实现。Concept 把“哪些类型可用”提升为声明的一部分，编译器在重载解析期间规范化并比较约束。

约束失败不是函数体编译失败：不满足的模板通常不会成为可行候选，诊断能指出哪个原子约束为假。函数体仍应只使用约束承诺的操作，否则错误依然会出现在实例化深处。

SFINAE 主要描述“某次模板参数替换是否形成有效声明”，而约束系统还把条件纳入候选之间的偏序。两个函数参数列表相同但约束强弱不同，编译器可以通过 subsumption 选择更受约束者，不必把优先级编码到额外标签或整数模板技巧中。

Concept 不是布尔类型别名，而是受特殊语法和规范化规则管理的命名约束。Concept 定义必须出现在命名空间作用域，不能显式特化或部分特化来偷偷改变某个类型的满足关系。需要扩展时，应组合更基础的 Concept 或把定制点建模成表达式能力。

约束检查只影响模板可用性，不会在运行期插入 `if`。同一个满足约束的模板仍按每组模板实参生成普通特化，ABI 和代码膨胀问题与其他模板相同。

## 定义与使用形式

Concept 是产生布尔常量的命名模板，可由类型萃取、其他 Concept 和 requires-expression 组成。使用方式包括受约束模板参数、尾部 `requires`、缩写函数模板参数以及 `requires` 子句。

`requires` 表达式可以检查表达式是否有效、返回类型是否满足 Concept、操作是否 `noexcept`，而不真正执行表达式。它描述的是语法和部分静态性质；诸如“加法满足结合律”这样的语义要求只能由文档和测试约束。

<!-- example id="cpp20-requires-expression" std="c++20" file="main.cpp" kind="single" compilers="all" output="sum=6" -->
```cpp
#include <concepts>
#include <cstddef>
#include <iostream>
#include <vector>

template <typename Range>
concept IntegerRange = requires(const Range& values) {
    typename Range::value_type;
    requires std::same_as<typename Range::value_type, int>;
    { values.size() } noexcept -> std::convertible_to<std::size_t>;
    { values.begin() };
    { values.end() };
};

template <IntegerRange Range>
int sum(const Range& values) {
    int result = 0;
    for (int value : values) {
        result += value;
    }
    return result;
}

int main() {
    const std::vector<int> values{1, 2, 3};
    static_assert(IntegerRange<decltype(values)>);
    std::cout << "sum=" << sum(values) << '\n';
}
```

这个 requires-expression 同时使用四类 requirement：

- `typename Range::value_type;` 是类型 requirement，只检查名称能否表示类型；
- `values.begin();` 是简单 requirement，只检查表达式可形成；
- `{ values.size() } noexcept -> convertible_to<size_t>;` 是复合 requirement，同时检查有效性、不抛属性和返回类型约束；
- `requires same_as<...>;` 是嵌套 requirement，要求另一个约束表达式为真。

requires-expression 在替换语境中遇到不合法 requirement 时通常产生 `false`，而不是直接让整个翻译失败。但若表达式对任何可能模板实参都无效，或错误发生在模板化语境之外，仍可能是硬错误。不要用它掩盖拼写错误。

### 四种约束放置方式

`template<Concept T>` 是受约束类型模板参数；`template<class T> requires Concept<T>` 是前置 requires-clause；函数声明尾部还可写尾置 requires-clause；`Concept auto` 形参会形成缩写函数模板。四者可以组合，但公共接口应选最易读且能表达参数关系的位置。

缩写形参每出现一个 `auto` 就引入独立模板参数。`void copy(Sized auto from, Sized auto to)` 不意味着两者同类型；需要相同类型时应显式写一个模板参数，或增加 `same_as<decltype(from), decltype(to)>` 关系约束。

Concept 也可约束普通 `auto` 变量和函数返回占位符的推导结果。它检查推导后的类型，却不会把运行期多态对象装进某个“Concept 对象”。若要运行期擦除仍需虚函数、`variant`、`any` 或专门 type erasure。

## 约束规范化与偏序

编译器把约束拆成原子约束并进行合取、析取规范化。更受约束的候选可在重载中优先，但逻辑上等价的不同写法未必产生相同原子身份。应复用命名 Concept，而不是到处重写相似布尔表达式，否则可能出现意外歧义。

短路规则让 `A<T> && B<T>` 在 A 不满足时不实例化 B，这对于先验证类型存在某成员、再检查成员性质很重要。

### 原子约束身份

原子约束是否相同，不只看最终布尔真值，也取决于它们来自哪个源表达式及参数映射。把同一条件抽成命名 Concept 并复用，能让编译器识别 subsumption 关系；在两个重载中分别手写 `is_integral_v<T>`，再拼接看似等价条件，可能无法得到预期偏序。

例如基础 Concept `Decrementable` 与组合 Concept `RevIterator = Decrementable<T> && requires ...` 共享同一个基础原子约束，所以 `RevIterator` 候选可被识别为更受约束。若后者重新写一遍递减表达式，它在源码层形成不同原子约束，重载可能歧义。

析取约束表达“满足任意一支”，合取表达“全部满足”。规范化会形成析取范式/合取范式用于比较，但编译器不进行任意数学定理证明。不要期待它推导 `sizeof(T) > 4` 必然蕴含 `sizeof(T) > 2`。

### 短路与依赖顺序

约束从左到右按规则实例化。先写能保护后续表达式的存在性检查，再访问依赖成员。例如先要求 `typename T::value_type`，再对该类型应用 Concept。把顺序颠倒可能在保护条件生效前触发无效名称。

Concept 定义本身应是稳定的语义接口。修改公共 Concept 的条件会改变大量重载可行性和特化选择，可能是源码兼容性变更，即便任何函数签名的文本都没变。

## 标准 Concepts 的语义层次

`same_as`、`derived_from`、`convertible_to`、`common_reference_with` 等描述类型关系；`integral`、`floating_point`、`signed_integral` 描述基础类别；`constructible_from`、`assignable_from`、`swappable` 描述对象操作；`invocable`、`predicate`、`relation` 描述调用协议。

部分标准 Concept 明确带有超出语法可检查范围的语义要求。例如 `equality_comparable` 期望相等关系满足规定性质，`strict_weak_order` 要求关系构成严格弱序。编译器只能验证表达式和类型，违反语义的类型仍可能“语法上满足”Concept，却使使用它的算法违反前置条件。

`convertible_to<From, To>` 比单纯 `is_convertible_v` 还要求相应显式转换表达式成立，并附带结果相等性等语义要求。选标准 Concept 时应阅读完整契约，而不是只根据名字猜测。

## 诊断与 API 设计

把所有实现细节都塞进 Concept 会让接口过度约束。例如算法只需 `begin/end` 和整数元素，却要求具体 `vector<int>`，会拒绝数组、span 和用户范围。反过来只检查 `begin/end` 而函数体又调用 `size()`，仍会产生深层实例化错误。

推荐从函数体真正使用的操作出发，再给这些操作提升业务语义。底层通用库用标准 Concepts 精确描述机制，上层领域接口可定义 `SortableRecordRange` 等命名约束，并在文档中补充不可静态检查的不变量。

负向编译测试很重要：验证错误类型在接口处被拒绝、诊断能指出有意义的 Concept，而不是意外落到另一个宽泛重载。运行测试则验证那些 Concept 无法证明的代数性质和业务前置条件。

## 编译器与运行时成本

Concept 完全在编译期工作，不为对象增加标签或虚调用。它可能增加约束检查工作，也常通过更早终止无效实例化改善诊断和构建体验。满足约束后的函数仍是普通模板实例。

## 示例解析与设计检查

示例把算术类别命名为 `Arithmetic`，又在 `add` 上增加“整数且至少四字节”的约束。真实 Concept 应尽量基于操作能力而非 `sizeof` 等偶然表示。审查时确认名称表达语义、约束不强于实现需要、重载之间存在明确偏序，并为不满足调用保留可理解诊断。

## 权威资料

- [约束与 Concepts](https://eel.is/c++draft/temp.constr)
- [P0734R0：Concepts 设计](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2017/p0734r0.pdf)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
