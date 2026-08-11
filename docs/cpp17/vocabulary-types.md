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

## `variant`：带判别值的联合

`variant<Ts...>` 保存足以容纳最大备选类型的内联存储、对齐填充和当前索引。切换备选时析构旧值并构造新值，不需要为备选本身做类型擦除。其大小至少受最大备选和判别信息影响。

异常发生在切换过程中时，variant 可能进入 `valueless_by_exception` 状态。`visit` 比连续 `holds_alternative/get` 更适合穷尽处理所有类型；访问者的重载集合可以让新增备选在编译期暴露遗漏。

## `any`：开放集合的类型擦除

`any` 保存任意可复制类型，并记录运行期类型信息以及销毁、复制等擦除操作。小对象可能内联，大对象通常堆分配，具体阈值由实现决定。`any_cast<T>` 要求类型精确匹配，不执行普通数值隐式转换。

开放性带来更晚的错误发现和更高成本。插件元数据、异构上下文等确实无法预先列举类型时才使用；领域状态通常应选择 `variant`。

## 示例解析与建模顺序

示例分别展示缺失性、封闭联合和开放元数据。建模时先问“状态集合能否列举”，再问“缺失是否需要原因”，最后才考虑 `any`。同时评估对象大小、复制成本、异常策略和序列化方式。

## 权威资料

- [P0088R3：variant](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0088r3.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
