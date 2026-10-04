# Concepts 与约束

阅读前建议先了解：[普通模板推导](../prerequisites.md#普通模板与类型推导)、[类型萃取](../cpp11/functional-tools.md#先分别使用-tuple-与类型萃取)；不必先掌握 SFINAE。本篇介绍的新增能力属于 C++20；后续版本差异会另行标注。

## 这个特性解决什么问题

模板参数的名字 T 不说明哪些类型可以传入。若函数需要整数，普通模板可能先接受字符串，再在函数体深处报错。C++20 Concept 把“允许的类型或操作”写在接口处：不满足约束时，该模板不是可用候选。

Concept 是一个命名的编译期条件，constraint（约束）是应用到模板的条件。它仍使用原来的模板实例化机制，不是新的运行期类型系统。先学会约束普通函数，再阅读 requires-expression（检查表达式是否合法）与重载选择。

## 先约束一个函数模板

传统代码可用 enable_if 与 is_integral 在声明中排除非整数类型；Concept 用命名条件表达同样的输入限制。下面两个函数对本例的整数输入都返回 42。

```cpp example id="cpp20-concept-basic-comparison" std="c++20" file="main.cpp" kind="single" compilers="all" output="old=42, modern=42"
#include <concepts>
#include <iostream>
#include <type_traits>

template <typename T>
typename std::enable_if<std::is_integral<T>::value, T>::type
old_twice(T value) { return value + value; }

template <std::integral T>
T twice(T value) { return value + value; }

static_assert(std::integral<int>);
static_assert(!std::integral<double>);

int main() {
    std::cout << "old=" << old_twice(21) << ", modern=" << twice(21) << '\n';
}
```

integral 是标准库定义的“整数类型”Concept，本例并不需要自行实现它。enable_if 的旧写法只用于对比，初学者可以先看现代声明。约束在编译期检查，不会为调用增加运行期 if。注意类型检查不能排除整数加法溢出等运行期错误。

不满足约束的调用应当在接口处被拒绝：

```text
twice(1.5); // double 不满足 integral：没有可用的 twice 候选
```

适合在泛型库与可复用接口中声明必要能力；只有一两个固定类型的业务函数可以直接写普通重载。Concept 不能静态验证排序关系、结合律等所有语义性质。

## 再读自定义约束的语法

下面的 `Addable` 表达两个要求：`left + right` 必须合法，且结果的类型必须恰好是 T。`requires(T left, T right)` 中的名字用于检查表达式，并不真正创建对象或执行加法；箭头后的 `std::same_as<T>` 检查结果类型。

`template <Addable T>` 和下面的 `requires Addable<T>` 是两种施加这个条件的写法，按需要选一种即可。

```text
template <typename T>
concept Addable = requires(T left, T right) {
    { left + right } -> std::same_as<T>;
};

template <Addable T> T combine(T, T);          // 受约束模板参数
template <typename T> requires Addable<T> T combine(T, T);
Addable auto normalize(Addable auto value);   // 缩写函数模板
```

## 组合示例：命名与组合约束

示例的 `Arithmetic` 组合两个标准 Concept，`add` 再附加整数宽度约束。约束在重载解析时检查，函数体不需要运行期类型分支。

```cpp example id="cpp20-concepts" std="c++20" file="main.cpp" kind="single" compilers="all" output="42"
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

程序输出 `42`。`twice(10)` 满足算术约束并得到 `20`，随后 `int` 同时满足 `integral` 和尺寸条件。Concept 应描述调用者真正依赖的语义能力，而不是只罗列碰巧使用的具体类型。

## 进一步理解：从 SFINAE 到约束系统

C++20 之前常把 `enable_if` 放进返回类型或模板参数，通过替换失败移除候选。这能工作，但接口难读，失败位置可能深入实现。Concept 把“哪些类型可用”提升为声明的一部分，编译器在重载解析期间规范化并比较约束。

约束失败不是函数体编译失败：不满足的模板通常不会成为可行候选，诊断能指出哪个原子约束为假。函数体仍应只使用约束承诺的操作，否则错误依然会出现在实例化深处。

SFINAE（模板参数替换失败时，从相应重载候选中移除该模板，而不是立即报错） 主要描述“某次模板参数替换是否形成有效声明”，而约束系统还把条件纳入候选之间的偏序（用来选择更合适的重载）。两个函数参数列表相同但约束强弱不同，编译器可以通过 subsumption 选择更受约束者，不必把优先级编码到额外标签或整数模板技巧中。

Concept 不是布尔类型别名，而是受特殊语法和规范化规则管理的命名约束。Concept 定义必须出现在命名空间作用域，不能显式特化或部分特化来偷偷改变某个类型的满足关系。需要扩展时，应组合更基础的 Concept 或把定制点建模成表达式能力。

约束检查只影响模板可用性，不会在运行期插入 `if`。同一个满足约束的模板仍按每组模板实参生成普通特化，ABI（二进制接口约定，例如调用方式与对象布局） 和代码膨胀问题与其他模板相同。

## 定义与使用形式

Concept 是产生布尔常量的命名模板，可由类型萃取、其他 Concept 和 requires-expression 组成。使用方式包括受约束模板参数、尾部 `requires`、缩写函数模板参数以及 `requires` 子句。

`requires` 表达式可以检查表达式是否有效、返回类型是否满足 Concept、操作是否 `noexcept`，而不真正执行表达式。它描述的是语法和部分静态性质；诸如“加法满足结合律”这样的语义要求只能由文档和测试约束。

```cpp example id="cpp20-requires-expression" std="c++20" file="main.cpp" kind="single" compilers="all" output="sum=6"
#include <concepts>
#include <cstddef>
#include <iostream>
#include <ranges>
#include <vector>

template <typename Range>
concept IntegerRange = std::ranges::input_range<const Range> &&
                       requires(const Range& values) {
    typename Range::value_type;
    requires std::same_as<typename Range::value_type, int>;
    requires std::same_as<std::ranges::range_value_t<const Range>, int>;
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

这里先用 input_range<const Range> 保证实际可遍历，再展示四类 requirement（要求）。仅有 begin/end 的名字并不能保证能递增、比较或读取元素；四类语法的教学约束也不是最简的真实求和接口：

- `typename Range::value_type;` 是类型 requirement，只检查名称能否表示类型；
- `values.begin();` 是简单 requirement，只检查表达式可形成；
- `{ values.size() } noexcept -> convertible_to<size_t>;` 是复合 requirement，同时检查有效性、不抛属性和返回类型约束；
- `requires same_as<...>;` 是嵌套 requirement，要求另一个约束表达式为真。

requires-expression 在替换语境中遇到不合法 requirement 时通常产生 `false`，而不是直接让整个翻译失败。但若表达式对任何可能模板实参都无效，或错误发生在模板化语境之外，仍可能是硬错误。不要用它掩盖拼写错误。

### requires-expression 的局部参数

`requires(T value, const U& other) { ... }` 中的参数只用于描述表达式的类型和值类别，不创建运行期对象，也没有存储、链接和生命周期。参数不能带默认实参，参数列表末尾也不能使用省略号表达 C 风格可变参数。数组和函数类型会按参数声明规则调整。

这意味着可以用 `T&& value` 精确检查右值操作，用 `const T&` 检查只读接口，而不要求 T 真能在运行期默认构造。局部参数的名字只在 requirement 序列内部可见。

复合 requirement `{ expression } noexcept -> Concept;` 按顺序检查：表达式能否形成、若写了 `noexcept` 是否确实不抛，最后把 `decltype((expression))` 作为首个模板实参交给返回类型 requirement 后的 Concept。双括号形式的 `decltype` 会保留引用和值类别，因此 `same_as<T>` 与 `same_as<T&>` 的选择必须准确。

类型 requirement `typename T::value_type;` 只证明该名称是类型，并不要求该类型完整、可构造或满足其他操作。若实现还要按值创建它，应继续增加 `default_initializable`、`movable` 等真正使用到的约束。

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

### 参数映射与不合法映射

复用 Concept 时，编译器会把外层模板参数映射到 Concept 定义中的参数，再形成原子约束。映射本身如果产生不合法类型，例如在不受保护的路径里形成 `V&*`，可能使程序不合法，而不是简单得到 false。组合约束要让“保护性”条件位于能短路后续映射的位置。

约束满足结果会参与声明匹配和实例化。依赖程序中稍后出现的显式特化、宏差异或不一致声明来改变同一原子约束真值，会破坏编译器缓存和 ODR（单一定义规则，约束一个程序中同一实体的多处声明和定义） 假设。Concept 所依赖的 traits 与定制点应在首次使用前稳定定义。

约束表达式的最终类型必须是 `bool`，不会像普通 `if` 条件那样接受任意显式/隐式“可转 bool”对象。类型萃取通常使用 `_v` 成员；把 `std::is_integral<T>` 类型对象本身误放进约束不是等价写法。

## 标准 Concepts 的语义层次

`same_as`、`derived_from`、`convertible_to`、`common_reference_with` 等描述类型关系；`integral`、`floating_point`、`signed_integral` 描述基础类别；`constructible_from`、`assignable_from`、`swappable` 描述对象操作；`invocable`、`predicate`、`relation` 描述调用协议。

部分标准 Concept 明确带有超出语法可检查范围的语义要求。例如 `equality_comparable` 期望相等关系满足规定性质，`strict_weak_order` 要求关系构成严格弱序。编译器只能验证表达式和类型，违反语义的类型仍可能“语法上满足”Concept，却使使用它的算法违反前置条件。

`convertible_to<From, To>` 比单纯 `is_convertible_v` 还要求相应显式转换表达式成立，并附带结果相等性等语义要求。选标准 Concept 时应阅读完整契约，而不是只根据名字猜测。

对象 Concept 也存在层级：`destructible`、`constructible_from`、`default_initializable`、`move_constructible`、`copy_constructible` 逐步组合能力；`movable` 还要求可赋值和可交换，`copyable` 在其上增加复制路径，`semiregular` 再增加默认构造，`regular` 最后加入相等可比较。名称描述的是整组语法与语义契约，不只是某一个同名特殊成员函数存在。

调用 Concept 中，`invocable` 只要求能按 `invoke` 形成调用，而 `regular_invocable` 还附带不修改函数对象/实参及相同输入产生相等输出等语义期望；`predicate` 在其上要求结果可用于布尔判断。编译器无法验证确定性和无副作用，算法作者仍需文档和测试。

标准 Concept 的模板参数顺序有时为偏序设计服务，例如 `derived_from<Derived, Base>`、`assignable_from<LHS, RHS>`。定义缩写接口时要确认被推导类型填入的是哪个位置；`Concept auto` 会把推导类型作为该 Concept 的第一个参数。

## 诊断与 API 设计

把所有实现细节都塞进 Concept 会让接口过度约束。例如算法只需 `begin/end` 和整数元素，却要求具体 `vector<int>`，会拒绝数组、span 和用户范围。反过来只检查 `begin/end` 而函数体又调用 `size()`，仍会产生深层实例化错误。

推荐从函数体真正使用的操作出发，再给这些操作提升业务语义。底层通用库用标准 Concepts 精确描述机制，上层领域接口可定义 `SortableRecordRange` 等命名约束，并在文档中补充不可静态检查的不变量。

负向编译测试很重要：验证错误类型在接口处被拒绝、诊断能指出有意义的 Concept，而不是意外落到另一个宽泛重载。运行测试则验证那些 Concept 无法证明的代数性质和业务前置条件。

## 编译器与运行时成本

Concept 完全在编译期工作，不为对象增加标签或虚调用。它可能增加约束检查工作，也常通过更早终止无效实例化改善诊断和构建体验。满足约束后的函数仍是普通模板实例。

## 示例解析与设计检查

示例把算术类别命名为 `Arithmetic`，又在 `add` 上增加“整数且至少四字节”的约束。真实 Concept 应尽量基于操作能力而非 `sizeof` 等偶然表示。审查时确认名称表达语义、约束不强于实现需要、重载之间存在明确偏序，并为不满足调用保留可理解诊断。

## 约束形式速查

| 形式 | 关键语义 |
| --- | --- |
| `template<C T>` | 约束一个模板类型参数 |
| `C auto value` | 缩写函数模板/占位类型约束 |
| 前置 `requires C<T>` | 位于模板头之后，适合参数总体条件 |
| 尾置 `requires` | 可引用函数形参相关类型/表达式 |
| 简单 requirement | 只检查表达式能否形成，不执行 |
| 类型 requirement | `typename T::x;` 只检查名称表示类型 |
| 复合 requirement | 可检查表达式、noexcept 和结果 Concept |
| 嵌套 requirement | `requires BooleanConstraint;` |
| 原子约束 | 身份源于表达式和参数映射，不只是真值 |
| subsumption | 通过规范化比较更受约束候选，不做任意定理证明 |

## Concepts 诊断阅读顺序

- 先找最外层“constraints not satisfied”的候选，而非立即阅读模板回溯底部。
- 展开命名 Concept，定位为假的具体原子 requirement。
- 若是表达式 requirement，分别核对对象 cv、引用类别和参数顺序。
- 若是返回约束，记住检查对象是 `decltype((expr))`，可能带引用。
- 若两个候选歧义，比较是否复用了同一命名基础 Concept。
- 若保护条件未生效，检查合取从左到右的实例化顺序。
- 若错误是硬错误，判断是否发生在非模板语境或参数映射本身不合法。
- 若标准 Concept 语法满足但算法出错，检查不可静态验证的代数语义。
- 若修改 trait 后结果不一致，检查首次约束检查前定义和各翻译单元 ODR。
- 将深层 requirement 提取成命名 Concept，通常能同时改善重用和诊断。

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp20/concepts.md
```

## 权威资料

- [约束与 Concepts](https://eel.is/c++draft/temp.constr)
- [P0734R0：Concepts 设计](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2017/p0734r0.pdf)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
