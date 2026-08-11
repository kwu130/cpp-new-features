# 类模板实参推导

类模板实参推导（CTAD）根据构造实参和推导指引推断模板参数，减少重复类型书写。

<!-- example id="cpp17-ctad" std="c++17" file="main.cpp" kind="single" compilers="all" output="items=3" -->
```cpp
#include <iostream>
#include <string>
#include <tuple>
#include <utility>

template <typename T>
class Box {
public:
    explicit Box(T value) : value_(std::move(value)) {}
    const T& get() const { return value_; }

private:
    T value_;
};

Box(const char*) -> Box<std::string>;

int main() {
    Box box("items=3");
    std::pair point(2, 5);
    std::tuple record(1, std::string("Ada"));
    (void)point;
    (void)record;
    std::cout << box.get() << '\n';
}
```

CTAD 只省略类模板实参，不会把类模板变成普通类型。自定义推导指引应反映构造函数的自然语义，避免同一调用产生意外类型。

## 推导候选如何产生

编译器为类模板的构造函数形成一组虚拟函数模板候选，再结合用户定义推导指引、复制推导候选等规则进行重载解析。选中候选的返回类型就是最终类模板特化类型，之后才真正调用该特化的构造函数。

因此“推导类型”和“构造对象”是两个阶段。推导指引没有函数体，也不在运行时执行；它只声明从参数类型到类模板实参的映射。

隐式候选大致保留类模板参数、构造函数模板参数和构造函数形参，并把返回类型视为相应类模板特化。除此之外，还有用户定义指引，以及从同类对象初始化时很重要的复制推导候选。所有候选一起参与类似函数重载解析的过程。

若模板参数没有出现在可推导的构造函数形参位置，隐式指引也无法凭空推断它。默认模板实参可以补足未推导参数，但默认构造函数并不意味着编译器知道应该选择哪个 `T`。

## 为什么需要自定义指引

字符串字面量直接按模板推导容易得到 `const char*` 或数组相关类型，而业务容器可能希望拥有 `std::string`。示例的 `Box(const char*) -> Box<std::string>` 把这种策略写在类型接口旁边。

指引过宽会产生悬空或意外复制。例如把任意 `T&` 推导成保存引用的包装器，需要确保包装器语义和生命周期明确。标准库也提供大量指引，让 `pair(1, 2.0)`、`tuple(...)` 等自然工作。

另一个典型场景是构造函数接收迭代器，而类模板参数应是迭代器的元素类型。构造函数模板本身只能推导 `Iterator`，无法反向得出类的 `T`；显式指引可以通过 `iterator_traits` 写出这层映射。

<!-- example id="cpp17-ctad-iterator-guide" std="c++17" file="main.cpp" kind="single" compilers="all" output="count=3, sum=6" -->
```cpp
#include <cstddef>
#include <iostream>
#include <iterator>
#include <type_traits>
#include <vector>

template <typename T>
class Buffer {
public:
    template <typename Iterator>
    Buffer(Iterator first, Iterator last) : values_(first, last) {}

    std::size_t size() const noexcept { return values_.size(); }

    T sum() const {
        T result{};
        for (const T& value : values_) {
            result += value;
        }
        return result;
    }

private:
    std::vector<T> values_;
};

template <typename Iterator>
Buffer(Iterator, Iterator)
    -> Buffer<typename std::iterator_traits<Iterator>::value_type>;

int main() {
    const std::vector<int> source{1, 2, 3};
    Buffer buffer(source.begin(), source.end());
    static_assert(std::is_same_v<decltype(buffer), Buffer<int>>);
    std::cout << "count=" << buffer.size() << ", sum=" << buffer.sum() << '\n';
}
```

指引先从迭代器类型取得 `value_type`，推导出 `Buffer<int>`，随后才用两个迭代器调用该特化中的构造函数。若两个迭代器来自不同类型，当前构造函数模板要求它们先共同推导成同一个 `Iterator`；需要哨兵类型时，接口和指引都要分别建模。

### 指引不是普通函数

推导指引写在与类模板相同的语义作用域中，没有名称、函数体或地址，不能直接调用。其尾部返回类型必须是所引导类模板的特化。它也不是类成员，因此不带访问说明符；实际构造函数是否可访问仍在对象构造阶段检查。

用户定义指引之间可能重载，也可能与隐式指引竞争。约束过宽的指引会抢占自然候选，所以应精确表达输入形态，并用编译期断言测试公开示例。

## 与函数模板推导的差异

CTAD 只用于声明对象等需要类类型的语境，不能在函数参数里单独写裸模板名来表达任意特化。复制初始化列表、聚合模板和别名模板的支持还会随标准版本演进，阅读代码时应确认最低语言版本。

C++17 不为聚合类模板自动生成聚合推导候选；如果类没有合适构造函数，通常需要显式推导指引。别名模板 CTAD 和更完整的聚合推导属于后续标准演进，不能写进以 C++17 为最低版本的示例。

函数形参中的 `Box` 仍不能表示“任意 `Box<T>`”。要接受所有特化，应写函数模板 `template<class T> void use(const Box<T>&)`。CTAD 发生在创建具体对象时，不是类型擦除、子类型多态或新的占位类型系统。

## ABI 与可维护性

调用点省略的类型仍是静态具体类型，运行时没有额外成本。但新增构造函数或推导指引可能改变旧调用的重载结果，属于源代码兼容性风险。公共库应测试关键推导表达式的 `decltype`。

推导结果会进入变量类型、重载选择和可能的符号名称。虽然推导本身不产生运行时 ABI 设施，但库升级后若同一源码推导成不同特化，行为、对象布局和调用目标都可能变化。把推导测试视为 API 契约测试，而不只是语法测试。

## 工程检查清单

只有自然且唯一的类型映射才让用户依赖 CTAD；所有权包装器谨慎处理字符串字面量和引用；用 `static_assert(is_same_v<...>)` 固化重要推导；当显式模板实参更能表达业务含义时不要追求省字。

## 复制推导候选

从某个 `C<U>` 对象构造 `C copy(original)` 时，语言加入类似 `C(C<U>) -> C<U>` 的复制推导候选。它通常让 CTAD 保留原特化，而不是把模板参数错误推成 `C<U>` 再形成 `C<C<U>>`。

若类自己有接受 C<U> 的构造模板/用户指引，候选偏序可能选择嵌套或转换语义。包装器类应测试从同类型、派生/可转换 wrapper 复制时的实际 `decltype`。

复制推导只决定目标特化；随后该特化仍需有可访问可行构造函数。推导成功不保证复制动作合法，例如 move-only 特化从 const 左值仍会在构造阶段失败。

## 初始化列表与候选阶段

类模板 deduction 的候选重载解析仍受列表初始化规则影响。若目标类/候选有 initializer_list 构造，花括号可能优先选择它；空列表又可能没有足够信息推导类模板参数。

`std::vector values{1,2,3}` 可由标准指引/构造推导为 vector<int>，但 `std::vector values(10, 20)` 的参数语义不同。CTAD 省略模板实参，不统一圆括号/花括号构造语义。

字符串字面量数组在按值候选中常衰减为 const char*，按引用候选可保留 N。自定义指引决定存 string、string_view、指针还是数组包装时，本质是在制定所有权 API。

### 显式构造与 copy-initialization

由 explicit 构造产生的隐式 deduction candidate 也带相应显式性质。copy-initialization 语境不能选最终 explicit 候选，直接初始化可能可以。`C c = args` 与 `C c(args)` 的可行性仍不同。

用户指引本身可声明 explicit（按版本规则），用于阻止隐式上下文产生意外类型。公共库要测试直接列表、复制列表、直接圆括号等所有承诺形式。

## 推导指引的维护

指引不是模板偏特化，不能有函数体或通过调用调试。可用 `static_assert(is_same_v<decltype(C(args...)), Expected>)` 建立编译期契约，并覆盖 cv/ref/数组/迭代器。

新增构造函数会自动生成新隐式候选，可能与旧用户指引竞争并改变源码行为。版本升级应把关键 CTAD 表达式纳入兼容测试。

过度聪明的指引会隐藏昂贵复制或借用生命周期。类型映射若需阅读实现才能理解，显式工厂名如 `make_owning_buffer` 更清楚。

## C++17 功能边界

别名模板 CTAD、聚合 deduction candidate 等能力在后续标准扩展。以 C++17 为最低版本时，为聚合模板手写指引，并通过原类模板名构造。

CTAD 不用于函数形参占位、基类列表任意省略或 `new` 的所有历史语境；具体语法支持随标准演进。文档示例必须用 `-std=c++17` 验证而非只在最新模式通过。

## 权威资料

- [P0091R3：类模板实参推导](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0091r3.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
