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

## 初始化语句的作用域

`if (init; condition)` 和 `switch (init; condition)` 让锁、迭代器、解析结果等临时对象只活在整个条件语句内，包括所有 `else` 分支。它减少名称泄漏，也让 RAII 对象在控制流结束时立即释放。

初始化语句只执行一次。若把锁放在其中，锁会覆盖条件判断和所选分支的整个执行期；这可能比预期临界区更大，应结合业务调整作用域。

## `if constexpr` 的实例化规则

条件必须是编译期布尔值。模板实例化时，不选中的分支成为 discarded statement，其中依赖模板参数的无效代码不会实例化。这使一个函数体能针对类型能力选择不同实现。

但被丢弃分支仍需在模板定义层面满足基本语法，且不依赖模板参数的明显错误仍可能被诊断。`if constexpr` 也不自动约束函数是否可调用；公共接口错误信息更适合 Concepts 或 SFINAE。

## 示例解析与工程实践

示例把查找迭代器限制在 `if` 内，再以引用分解映射元素，最后按整数类型选择编译期分支。实践中先决定绑定是否拥有数据，缩小初始化对象作用域，并把类型分派逻辑保持短小；复杂分支应拆到分别可测试的函数。
