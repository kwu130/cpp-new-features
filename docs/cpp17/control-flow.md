# 结构化绑定与条件语句增强

结构化绑定可以为数组、元组和类似结构体的成员命名。`if`/`switch` 初始化语句缩短临时对象作用域，`if constexpr` 则在编译期丢弃不适用分支。

<!-- example id="cpp17-control-flow" std="c++17" file="main.cpp" kind="single" compilers="all" output="answer=42" -->
```cpp
#include <iostream>
#include <map>
#include <string>
#include <type_traits>
#include <utility>

template <typename T>
void print_value(const T& value) {
    if constexpr (std::is_integral_v<T>) {
        std::cout << "answer=" << value << '\n';
    } else {
        std::cout << value << '\n';
    }
}

int main() {
    std::map<std::string, int> values{{"answer", 42}};
    if (const auto iterator = values.find("answer"); iterator != values.end()) {
        const auto& [name, value] = *iterator;
        (void)name;
        print_value(value);
    }
}
```

结构化绑定使用 `auto`、`auto&` 或 `const auto&` 时同样需要考虑复制。`if constexpr` 只会丢弃依赖模板参数的不适用代码，它不是普通运行期条件的替代品。

## 结构化绑定的三种协议

结构化绑定会先创建一个隐藏变量，再为其元素建立名称。数组按下标分解；类若满足 `tuple_size` 协议，则通过 `get<I>` 与 `tuple_element` 分解；否则可分解可访问的非静态数据成员。绑定名称不是普通引用变量的简单语法替换，其 `decltype` 规则要结合隐藏对象和元素类型判断。

`auto [a, b] = object` 通常会复制或移动出一个隐藏对象；`auto& [a, b] = object` 绑定原对象；`const auto&` 既避免复制又禁止通过绑定修改。映射遍历中元素类型是 `pair<const Key, Value>`，按值绑定会复制键和值。

### 隐藏对象与引用限定

对 `auto [x, y] = expression`，可以先概念化为创建一个名字不可见的变量 `e`，再让 `x`、`y` 指向 `e` 的组成部分。`const`、`volatile` 和 `&`/`&&` 修饰的是这个隐藏对象的声明，而不是把方括号中的每个名字分别声明成普通引用变量。

这解释了几个容易混淆的行为：按值分解时修改绑定不会修改原对象；按引用分解时会；用 `const auto&` 可以把临时对象的生命周期延长到绑定作用域结束。绑定数量必须与数组长度、`tuple_size` 或可分解成员数量完全一致，不能只取前几个元素。

`decltype(name)` 对结构化绑定有专门规则，得到协议所定义的“被引用类型”；`decltype((name))` 则按普通带括号表达式规则反映值类别，通常是左值引用类型。泛型代码若要保留表达式类别，应继续使用双括号形式。

### 自定义 tuple-like 协议

用户类型可以通过 `tuple_size`、`tuple_element<I, T>` 和可由成员查找或 ADL 找到的 `get<I>` 参与元组式分解。普通非限定名称查找不会替代协议规定的查找过程，因此 `get` 应与类型位于同一命名空间，或者作为成员模板提供。

<!-- example id="cpp17-custom-structured-binding" std="c++17" file="main.cpp" kind="single" compilers="all" output="rgb=10,25,30" -->
```cpp
#include <cstddef>
#include <iostream>
#include <tuple>

namespace graphics {

struct Rgb {
    int red;
    int green;
    int blue;
};

template <std::size_t Index>
int& get(Rgb& color) noexcept {
    static_assert(Index < 3, "RGB component index is out of range");
    if constexpr (Index == 0) {
        return color.red;
    } else if constexpr (Index == 1) {
        return color.green;
    } else {
        return color.blue;
    }
}

}  // namespace graphics

namespace std {

template <>
struct tuple_size<graphics::Rgb> : integral_constant<size_t, 3> {};

template <size_t Index>
struct tuple_element<Index, graphics::Rgb> {
    static_assert(Index < 3, "RGB component index is out of range");
    using type = int;
};

}  // namespace std

int main() {
    graphics::Rgb color{10, 20, 30};
    auto& [red, green, blue] = color;
    green += 5;
    std::cout << "rgb=" << red << ',' << green << ',' << blue << '\n';
}
```

标准允许为用户定义类型特化 `tuple_size` 和 `tuple_element`，但不能向 `std` 命名空间随意添加普通函数或不被允许的模板特化。例中 `get` 留在 `graphics`，由参数关联查找发现。`auto&` 使三个名称最终关联原对象成员，所以修改 `green` 会更新 `color.green`。

## 初始化语句的作用域

`if (init; condition)` 和 `switch (init; condition)` 让锁、迭代器、解析结果等临时对象只活在整个条件语句内，包括所有 `else` 分支。它减少名称泄漏，也让 RAII 对象在控制流结束时立即释放。

初始化语句只执行一次。若把锁放在其中，锁会覆盖条件判断和所选分支的整个执行期；这可能比预期临界区更大，应结合业务调整作用域。

初始化语句和条件中声明的名称处在同一声明区域，并在 `then` 与 `else` 两个分支都可见。它们的析构发生在整个选择语句结束后。`switch (init; condition)` 同样如此：初始化对象会跨越被选中的 `case` 执行期，而不是在条件求值后立刻销毁。

初始化部分既可以是简单声明，也可以是表达式语句；分号是语法的一部分。若声明了多个需要相同声明说明符的对象，仍应避免让初始化逻辑变得难以阅读。

## `if constexpr` 的实例化规则

条件必须是编译期布尔值。模板实例化时，不选中的分支成为 discarded statement，其中依赖模板参数的无效代码不会实例化。这使一个函数体能针对类型能力选择不同实现。

但被丢弃分支仍需在模板定义层面满足基本语法，且不依赖模板参数的明显错误仍可能被诊断。`if constexpr` 也不自动约束函数是否可调用；公共接口错误信息更适合 Concepts 或 SFINAE。

在模板外，未选择分支仍会被完整检查，不能用 `if constexpr(false)` 注释掉语法或类型错误。即使在模板内，一个对所有可能模板实参都无效、且与模板参数无关的语句也不能依靠丢弃分支获得可移植性。

每个分支可以返回不同类型，只要实例化后实际保留的返回语句能形成一致的 `auto` 返回类型。这让函数可以按类型选择表示方式，但若差异会传播到公共 API，显式重载通常更清楚。

## 示例解析与工程实践

示例把查找迭代器限制在 `if` 内，再以引用分解映射元素，最后按整数类型选择编译期分支。实践中先决定绑定是否拥有数据，缩小初始化对象作用域，并把类型分派逻辑保持短小；复杂分支应拆到分别可测试的函数。

## 权威资料

- [P0217R3：结构化绑定规范措辞](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0217r3.html)
- [P0305R1：带初始化语句的选择语句](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0305r1.html)
- [P0292R2：if constexpr](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0292r2.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
