# `optional`、`variant` 与 `any`

阅读前建议先了解：[对象生命周期](../prerequisites.md#对象生命周期与引用)、[Lambda](../cpp11/lambdas.md)；先分别学习三种状态类型。本篇介绍的新增能力属于 C++17；后续版本差异会另行标注。

## 先确定要表达哪种结果

普通 `int` 表示“一定有一个整数”。如果接口还需要表达缺失或不同类型，就需要把这些情况写进返回类型，而不是约定 `-1` 是失败、再让调用者记住约定。

| 需求 | 选择 | 例子 |
| --- | --- | --- |
| 可能没有值 | `optional<T>` | 查询用户年龄，可能未填写 |
| 值来自已知几种类型之一 | `variant<A, B>` | 配置项可以是整数或字符串 |
| 无法在接口中列全要保存的类型 | `any` | 插件附带的数据 |

三种工具可以分别使用。下面先看最小例，再看组合练习；内存布局和异常细节放在后半篇。

## optional：有年龄，或者没填写

传统接口可能用 `-1` 表示缺失，或返回 bool 并通过参数输出年龄。`optional<int>` 把“有无”和“整数”放在同一个返回值中。

```cpp example id="cpp17-optional-basic" std="c++17" file="main.cpp" kind="single" compilers="all" output="age=20, missing=true"
#include <iostream>
#include <optional>
std::optional<int> find_age(bool provided) {
    if (!provided) return std::nullopt;
    return 20;
}
int main() {
    const auto known = find_age(true);
    const auto unknown = find_age(false);
    if (known) {
        std::cout << "age=" << *known;
    }
    std::cout << ", missing=" << std::boolalpha << !unknown << '\n';
}
```

`nullopt` 表示没有值，`if (known)` 检查是否有值，`*known` 才取出整数。空 optional 不是整数 0，也不是默认构造出的一个 int；它不携带缺失原因，需要错误原因可读 C++23 的 [`expected`](../cpp23/expected.md)。

## variant：在已知选项中保存一种

如果配置项只允许整数和文本，传统写法需要类型标签配合 union 或多个字段。`variant<int, std::string>` 同时管理当前类型与值。

```cpp example id="cpp17-variant-basic" std="c++17" file="main.cpp" kind="single" compilers="all" output="integer=42, text=auto"
#include <iostream>
#include <string>
#include <variant>
int main() {
    std::variant<int, std::string> setting = 42;
    if (const int* number = std::get_if<int>(&setting)) {
        std::cout << "integer=" << *number;
    }
    setting = std::string("auto");
    if (const std::string* text = std::get_if<std::string>(&setting)) {
        std::cout << ", text=" << *text << '\n';
    }
}
```

第一次保存整数，赋值后改为字符串。`get_if` 在类型匹配时返回指针，否则返回空指针，所以判断成功后才能解引用。可选类型在声明中列出；不能任意放入一个未列出的对象。需要为每种类型执行不同逻辑时，后文再介绍 `visit`。

## any：保存开放类型，取值时确认

相比 `void*` 加手工管理寿命，`any` 会管理所保存对象的构造、复制和销毁。不过调用者仍须知道要取出的类型。

```cpp example id="cpp17-any-basic" std="c++17" file="main.cpp" kind="single" compilers="all" output="tag=cpp17, integer=false"
#include <any>
#include <iostream>
#include <string>
int main() {
    std::any metadata = std::string("cpp17");
    if (const auto* text = std::any_cast<std::string>(&metadata)) {
        std::cout << "tag=" << *text;
    }
    std::cout << ", integer=" << std::boolalpha
              << (std::any_cast<int>(&metadata) != nullptr) << '\n';
}
```

这里使用指针形式的 `any_cast`：类型不匹配返回空指针，不抛异常。`any_cast<int>` 不会把字符串解析为整数，也不会自动执行普通数值转换。保存的类型须可复制；类型集合已知时，优先考虑 variant，便于编译器检查处理是否齐全。

## 组合练习：识别三种不同状态

示例同时展示三种状态，但真实接口通常只选其中最准确的一种。这里检查 optional 和 variant 的状态；any 的类型由前面的构造语句确定。

```cpp example id="cpp17-vocabulary-types" std="c++17" file="main.cpp" kind="single" compilers="all" output="answer=42, tag=cpp17"
#include <any>
#include <iostream>
#include <optional>
#include <string>
#include <variant>

std::optional<int> parse_answer(bool available) {
    return available ? std::optional<int>{42} : std::nullopt;
}

int main() {
    const auto answer = parse_answer(true);
    std::variant<int, std::string> value = std::string("cpp17");
    std::any metadata = std::string("answer");

    if (!answer || !std::holds_alternative<std::string>(value)) {
        return 1;
    }
    std::cout << std::any_cast<std::string>(metadata) << '=' << *answer
              << ", tag=" << std::get<std::string>(value) << '\n';
}
```

程序输出 `answer=42, tag=cpp17`。`answer` 的有值状态和 `value` 的字符串备选经过检查；`metadata` 刚被构造为字符串，因此这里直接使用值形式的 `any_cast`。错误的 `get` 或值形式 `any_cast` 会抛出异常；可通过查询函数、访问器或指针形式转换设计无异常分支。

## `optional`：零个或一个值

`optional<T>` 通常在对象内部预留 `T` 的对齐存储，再用布尔状态记录是否已构造，不会为普通 T 自动进行堆分配。空状态不构造 T；`emplace` 在内部存储中直接构造；`reset` 析构当前值。

它适合“没有结果”是正常分支的场景，但不能携带详细失败原因。解析错误需要诊断时应使用包含错误类型的结果设计。访问前用布尔判断、`value_or` 或受控 `value()`；对空对象解引用违反前置条件。

### 构造、访问和状态转换

`nullopt` 明确构造空状态，`in_place` 和 `emplace(args...)` 直接在内部存储构造 `T`。赋值另一个值时，行为取决于当前是否已有对象：可能调用赋值运算，也可能先构造或销毁。`has_value()` 与显式布尔转换只查询状态。

`value()` 在空状态抛出 `bad_optional_access`；`operator*` 和 `operator->` 不承担这种检查。`value_or(default)` 按值返回，默认值要能转换为 `T`，并可能引入复制或移动。若 `T` 很大且只需观察，先判断后解引用更容易控制成本。

`optional<T>` 不能直接持有引用、`void` 或数组。需要“可空引用”时，可考虑指针或 `optional<reference_wrapper<T>>`，并明确被引用对象生命周期。`optional<bool>` 表达的是三种状态，而不是普通二值布尔的替代品。

### 布局与异常保证

实现通常把判别状态与一块能容纳 `T` 的内联存储放在一起，所以 `optional<T>` 的尺寸一般大于 `T`，对齐至少满足 `T`。它并不承诺利用 `T` 的某个特殊位模式压缩状态。`emplace` 会先销毁旧值再尝试构造新值；新构造抛出时对象成为空状态。

### 比较、哈希与嵌套语义

空 `optional` 与 `nullopt` 相等，并在关系排序中位于任意有值对象之前；两个有值对象再比较内部 `T`。这使它能自然参与排序，但也意味着排序语义不是“缺失值放最后”，业务若有不同要求必须提供比较器。标准为满足条件的 `optional<T>` 提供哈希支持，有值时基于 `T` 的哈希，空状态使用实现定义结果。

`optional<optional<T>>` 有三个可区分层次：外层为空、外层有值但内层为空、两层都有值。它有时能表达“字段未提供 / 明确清除 / 提供新值”，但若没有这类协议语义，嵌套会增加误解，宜改为领域枚举或 variant。

从 `T` 构造和赋值 `optional<T>` 时会参与一组条件化重载。泛型封装里尤其要留意 `optional<bool>` 等目标，因为“从某个 optional 转成 bool”与“从其内部值构造 bool”可能涉及微妙的重载规则；跨标准版本还存在缺陷修正差异，应对实际支持矩阵编译测试。

## `variant`：带判别值的联合

`variant<Ts...>` 保存足以容纳最大备选类型的内联存储、对齐填充和当前索引。切换备选时析构旧值并构造新值，不需要为备选本身做类型擦除。其大小至少受最大备选和判别信息影响。

异常发生在切换过程中时，variant 可能进入 `valueless_by_exception` 状态。`visit` 比连续 `holds_alternative/get` 更适合穷尽处理所有类型；访问者的重载集合可以让新增备选在编译期暴露遗漏。

第一个备选类型决定默认构造行为：若第一个类型可默认构造，默认 `variant` 持有它并令 `index()==0`。可把 `monostate` 放在首位，为本来都不可默认构造的备选集合提供显式空壳状态。重复类型合法，但这时按类型调用 `get<T>`/`holds_alternative<T>` 要求 `T` 在列表中恰好出现一次；按索引访问更明确。

`get<I>` 或 `get<T>` 选择错误会抛 `bad_variant_access`，指针风格的 `get_if` 在不匹配时返回空指针。`index()` 返回当前零基索引；无值异常状态返回 `variant_npos`。代码即使认为所有构造都不抛，也应理解该状态对泛型接口的影响。

```cpp example id="cpp17-variant-visitor" std="c++17" file="main.cpp" kind="single" compilers="all" output="integer=42, text=cpp17"
#include <iostream>
#include <string>
#include <variant>

template <typename... Functions>
struct Overloaded : Functions... {
    using Functions::operator()...;
};

template <typename... Functions>
Overloaded(Functions...) -> Overloaded<Functions...>;

int main() {
    const auto printer = Overloaded{
        [](int value) { std::cout << "integer=" << value; },
        [](const std::string& value) { std::cout << "text=" << value; }
    };

    std::variant<int, std::string> value = 42;
    std::visit(printer, value);
    std::cout << ", ";
    value = std::string("cpp17");
    std::visit(printer, value);
    std::cout << '\n';
}
```

`Overloaded` 用继承合并多个 Lambda 的调用运算符，显式推导指引让 C++17 可以构造这个聚合模板。`visit` 对每个备选检查访问者是否可调用，并要求所有组合产生满足接口规则的结果；它不是运行期逐个尝试 `dynamic_cast`，而是基于判别索引分派到已实例化的调用路径。

### 访问复杂度与组合爆炸

访问单个 variant 时，实现通常根据索引跳转。多 variant 同时访问需要覆盖备选类型的笛卡尔积，模板实例化数量可能迅速增长。若两个状态机各有十个备选，访问者需要在类型层面应对最多一百种组合；必要时先在领域层降低状态数量或分阶段分派。

### 备选选择与转换构造

从一个普通值构造或赋值 `variant` 时，标准通过近似重载决议选择唯一可接受备选，而不是简单选择“第一个能转换的类型”。若没有唯一最佳候选，表达式不成立；数值窄化相关候选还会被排除。工程上应避免让多个备选形成模糊的隐式转换网络，必要时用 `in_place_type<T>` 或 `in_place_index<I>` 明确指定目标。

`emplace<I>(args...)` 或 `emplace<T>(args...)` 直接切换并构造备选。按类型版本仍要求该类型恰好出现一次。切换通常需要先销毁旧备选；新构造若抛出，就可能产生无值异常状态。若目标类型具有不抛移动构造，实现有时可以通过临时对象缩小无值窗口，但程序不能据此假定状态永远存在。

访问器对所有实际组合都必须形成有效调用。C++17 的 `visit` 要求结果类型满足统一规则，不能让一个分支返回 `int`、另一个分支返回无关的 `string` 后期待运行期再决定静态返回类型。对状态集合新增备选后，重载访问器产生的编译错误通常正是需要补齐领域处理的信号。

## `any`：开放集合的类型擦除

`any` 保存任意可复制类型，并记录运行期类型信息以及销毁、复制等擦除操作。小对象可能内联，大对象通常堆分配，具体阈值由实现决定。`any_cast<T>` 要求类型精确匹配，不执行普通数值隐式转换。

开放性带来更晚的错误发现和更高成本。插件元数据、异构上下文等确实无法预先列举类型时才使用；领域状态通常应选择 `variant`。

### 管理函数与小对象优化

典型实现除存储区外还保留一个管理函数指针或等价表项。这个擦除层知道真实类型，负责销毁、复制、移动以及返回类型信息。`type()` 在有值时返回所存类型的 `type_info`，空 `any` 返回 `typeid(void)`。

小对象优化是否启用、阈值多大都不属于可移植契约。即使对象尺寸很小，若移动构造可能抛出，实现也可能选择堆分配以维持 `any` 移动操作的保证。性能关键代码应测量目标标准库，不能通过猜测阈值设计 ABI（二进制接口约定，例如调用方式与对象布局）。

`any` 要求所存对象可复制构造，因为复制 `any` 必须复制被擦除值；独占所有权的 `unique_ptr` 不能直接作为值放入。`emplace<T>` 会清除旧值并构造新值，失败时对象可能为空。`reset()` 销毁当前值，`has_value()` 查询是否非空。

`any_cast<T>(&object)` 的指针重载不抛异常，类型不精确匹配时返回空指针，适合探测开放元数据。值/引用重载不匹配会抛 `bad_any_cast`。顶层 cv 和引用会影响返回形式，但底层类型匹配不会执行数值提升或用户定义转换。

### 复制、移动与 ABI 边界

移动 `any` 后，源对象处于有效但具体是否为空由相应操作语义决定，代码应把它当作待重新赋值或安全查询的对象，而不是依赖某个实现的缓冲区交换方式。复制可能调用所存类型的复制构造并抛出；若应用禁用异常，开放的 `any` 边界需要额外约束可存类型和失败策略。

`any::type()` 和 `any_cast` 依赖运行期类型标识。即使两个共享库里存在源码上同名类型，若违反 ODR（单一定义规则，约束一个程序中同一实体的多处声明和定义）、使用不兼容 ABI 或跨越不一致的 RTTI 配置，也不能把 `any` 当作稳定互操作协议。长期存储和进程边界应使用显式 schema、版本号与序列化格式。

### 三者的资源与引用稳定性

`optional` 和 `variant` 的值通常位于包装对象内部，因此包装对象移动、销毁或切换状态会影响指向内部值的引用。`any` 可能内联也可能堆分配，标准不承诺移动后内部对象地址保持不变。不要长期保存由 `*optional`、`get` 或 `any_cast<T&>` 获得的引用，除非外围对象及其状态变更规则完全受控。

## 三种词汇类型对照

| 需求/接口 | `optional` | `variant` | `any` |
| --- | --- | --- | --- |
| 状态集合 | 空或一个 T | 编译期封闭 Ts 集合 | 运行期开放可复制类型 |
| 空状态 | `nullopt` | 可用 monostate 建模 | 默认构造/`reset` |
| 查询 | `has_value` | `index`/`holds_alternative` | `has_value`/`type` |
| 安全探测 | 布尔判断 | `get_if` | 指针版 `any_cast` |
| 错误访问 | `value` 抛 `bad_optional_access` | `get` 抛 `bad_variant_access` | 值版 `any_cast` 抛 `bad_any_cast` |
| 原位构造 | `emplace` | `emplace<I/T>` | `emplace<T>` |
| 存储模型 | 通常内联 T + 状态 | 最大备选内联存储 + 索引 | 小对象优化或堆由实现决定 |
| 穷尽处理 | 单一值分支 | `visit` 可编译期覆盖备选 | 调用方运行期约定类型 |
| 无值异常态 | 空 optional | `valueless_by_exception` | 构造失败后可能为空 |
| 选择原则 | 正常缺失 | 有限代数数据类型 | 真正开放扩展边界 |

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp17/vocabulary-types.md
```

## 权威资料

- [P0088R3：variant](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0088r3.html)
- [工作草案：optional](https://eel.is/c++draft/optional)
- [工作草案：any](https://eel.is/c++draft/any)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
