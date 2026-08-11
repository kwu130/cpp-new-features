# `optional`、`variant` 与 `any`

三种词汇类型分别表达“可能没有值”“有限类型集合中的一个值”和“运行期可保存任意可复制类型”。

<!-- example id="cpp17-vocabulary-types" std="c++17" file="main.cpp" kind="single" compilers="all" output="answer=42, tag=cpp17" -->
```cpp
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

优先选最具体的类型：可缺失用 `optional`，封闭类型集合用 `variant`，只有边界确实开放时才使用 `any`。错误的 `get` 或 `any_cast` 会抛出异常，也可先查询或使用指针形式转换。

## `optional`：零个或一个值

`optional<T>` 通常在对象内部预留 `T` 的对齐存储，再用布尔状态记录是否已构造，不会为普通 T 自动进行堆分配。空状态不构造 T；`emplace` 在内部存储中直接构造；`reset` 析构当前值。

它适合“没有结果”是正常分支的场景，但不能携带详细失败原因。解析错误需要诊断时应使用包含错误类型的结果设计。访问前用布尔判断、`value_or` 或受控 `value()`；对空对象解引用违反前置条件。

### 构造、访问和状态转换

`nullopt` 明确构造空状态，`in_place` 和 `emplace(args...)` 直接在内部存储构造 `T`。赋值另一个值时，行为取决于当前是否已有对象：可能调用赋值运算，也可能先构造或销毁。`has_value()` 与显式布尔转换只查询状态。

`value()` 在空状态抛出 `bad_optional_access`；`operator*` 和 `operator->` 不承担这种检查。`value_or(default)` 按值返回，默认值要能转换为 `T`，并可能引入复制或移动。若 `T` 很大且只需观察，先判断后解引用更容易控制成本。

`optional<T>` 不能直接持有引用、`void` 或数组。需要“可空引用”时，可考虑指针或 `optional<reference_wrapper<T>>`，并明确被引用对象生命周期。`optional<bool>` 表达的是三种状态，而不是普通二值布尔的替代品。

### 布局与异常保证

实现通常把判别状态与一块能容纳 `T` 的内联存储放在一起，所以 `optional<T>` 的尺寸一般大于 `T`，对齐至少满足 `T`。它并不承诺利用 `T` 的某个特殊位模式压缩状态。`emplace` 会先销毁旧值再尝试构造新值；新构造抛出时对象成为空状态。

## `variant`：带判别值的联合

`variant<Ts...>` 保存足以容纳最大备选类型的内联存储、对齐填充和当前索引。切换备选时析构旧值并构造新值，不需要为备选本身做类型擦除。其大小至少受最大备选和判别信息影响。

异常发生在切换过程中时，variant 可能进入 `valueless_by_exception` 状态。`visit` 比连续 `holds_alternative/get` 更适合穷尽处理所有类型；访问者的重载集合可以让新增备选在编译期暴露遗漏。

第一个备选类型决定默认构造行为：若第一个类型可默认构造，默认 `variant` 持有它并令 `index()==0`。可把 `monostate` 放在首位，为本来都不可默认构造的备选集合提供显式空壳状态。重复类型合法，但这时按类型调用 `get<T>`/`holds_alternative<T>` 要求 `T` 在列表中恰好出现一次；按索引访问更明确。

`get<I>` 或 `get<T>` 选择错误会抛 `bad_variant_access`，指针风格的 `get_if` 在不匹配时返回空指针。`index()` 返回当前零基索引；无值异常状态返回 `variant_npos`。代码即使认为所有构造都不抛，也应理解该状态对泛型接口的影响。

<!-- example id="cpp17-variant-visitor" std="c++17" file="main.cpp" kind="single" compilers="all" output="integer=42, text=cpp17" -->
```cpp
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

## `any`：开放集合的类型擦除

`any` 保存任意可复制类型，并记录运行期类型信息以及销毁、复制等擦除操作。小对象可能内联，大对象通常堆分配，具体阈值由实现决定。`any_cast<T>` 要求类型精确匹配，不执行普通数值隐式转换。

开放性带来更晚的错误发现和更高成本。插件元数据、异构上下文等确实无法预先列举类型时才使用；领域状态通常应选择 `variant`。

### 管理函数与小对象优化

典型实现除存储区外还保留一个管理函数指针或等价表项。这个擦除层知道真实类型，负责销毁、复制、移动以及返回类型信息。`type()` 在有值时返回所存类型的 `type_info`，空 `any` 返回 `typeid(void)`。

小对象优化是否启用、阈值多大都不属于可移植契约。即使对象尺寸很小，若移动构造可能抛出，实现也可能选择堆分配以维持 `any` 移动操作的保证。性能关键代码应测量目标标准库，不能通过猜测阈值设计 ABI。

`any` 要求所存对象可复制构造，因为复制 `any` 必须复制被擦除值；独占所有权的 `unique_ptr` 不能直接作为值放入。`emplace<T>` 会清除旧值并构造新值，失败时对象可能为空。`reset()` 销毁当前值，`has_value()` 查询是否非空。

`any_cast<T>(&object)` 的指针重载不抛异常，类型不精确匹配时返回空指针，适合探测开放元数据。值/引用重载不匹配会抛 `bad_any_cast`。顶层 cv 和引用会影响返回形式，但底层类型匹配不会执行数值提升或用户定义转换。

## 示例解析与建模顺序

示例分别展示缺失性、封闭联合和开放元数据。建模时先问“状态集合能否列举”，再问“缺失是否需要原因”，最后才考虑 `any`。同时评估对象大小、复制成本、异常策略和序列化方式。

三种类型都把状态放进类型系统，但保证程度不同：`optional<T>` 固定一个值类型和缺失状态；`variant<Ts...>` 固定有限集合并允许编译期穷尽；`any` 只保证运行期携带某个可复制类型。越开放，调用方能获得的静态检查越少。

跨共享库或插件边界传递 `any` 还需要考虑 RTTI、标准库 ABI 和分配器边界。稳定协议通常应使用显式标签加稳定数据格式，而不是直接暴露 `any` 的进程内表示。

## 权威资料

- [P0088R3：variant](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0088r3.html)
- [工作草案：optional](https://eel.is/c++draft/optional)
- [工作草案：any](https://eel.is/c++draft/any)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
