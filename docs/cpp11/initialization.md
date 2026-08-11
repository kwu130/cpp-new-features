# 统一初始化、初始化列表与 `nullptr`

花括号初始化为对象、容器和聚合类型提供统一写法，并阻止部分窄化转换。`nullptr` 则替代了容易与整数混淆的 `0` 和 `NULL`。

<!-- example id="cpp11-initialization" std="c++11" file="main.cpp" kind="single" compilers="all" output="3 points, first=1" -->
```cpp
#include <cstddef>
#include <initializer_list>
#include <iostream>
#include <vector>

class Points {
public:
    Points(std::initializer_list<int> values) : values_(values) {}
    std::size_t size() const { return values_.size(); }
    int first() const { return values_.front(); }

private:
    std::vector<int> values_;
};

int main() {
    Points points{1, 2, 3};
    int* pointer = nullptr;
    if (pointer == nullptr) {
        std::cout << points.size() << " points, first=" << points.first() << '\n';
    }
}
```

## 实践建议

新代码优先使用花括号初始化和 `nullptr`。但类同时拥有普通构造函数和 `initializer_list` 构造函数时，花括号会优先匹配后者，应确认这正是预期语义。

窄化写法如 `int value{3.14};` 会在编译期被拒绝，这类反例不放入可执行代码围栏。

## 学习目标

本章需要掌握直接列表初始化、复制列表初始化、聚合初始化和 `initializer_list` 构造的优先级，并理解为什么 `nullptr` 能解决空指针重载歧义。

## 初始化形式

`T object{args...}` 是直接列表初始化，`T object = {args...}` 是复制列表初始化。两者都会检查窄化，但后者不会调用 `explicit` 构造函数。空花括号通常执行值初始化：算术成员归零，类类型调用默认构造函数。

列表初始化的构造函数选择分两阶段进行：编译器先只考虑 `std::initializer_list` 构造函数；只有没有可行候选时才考虑其他构造函数。这解释了为什么 `std::vector<int>{10, 20}` 创建两个元素，而 `std::vector<int>(10, 20)` 创建十个值为 20 的元素。

窄化检查关注可能丢失信息的隐式转换，例如浮点到整数、超出范围的整数转换，以及非常量整数到更窄类型。若确实接受损失，应使用显式转换，让代码审查者看见意图。

## `initializer_list` 的对象模型

编译器通常为花括号中的元素创建一个临时只读数组，`initializer_list` 只保存指向该数组的起始指针和长度。复制 `initializer_list` 不会复制元素；它仍然观察同一段临时存储。元素类型是 `const T`，因此不能从列表元素直接移动出只移动对象。

临时数组生命周期会延长到绑定的 `initializer_list` 对象生命周期，但把其指针保存到更长寿命对象中仍会悬空。构造函数应在调用期间复制所需内容，而不是长期保存 `begin()`。

## `nullptr` 的类型原理

`nullptr` 的类型是 `std::nullptr_t`。它能隐式转换为任意指针或成员指针，却不会像整数 `0` 那样优先匹配整数重载。它不占用“特殊地址对象”；转换后的空指针表示仍由目标指针类型和平台 ABI 决定。

## 示例解析与工程建议

示例的 `Points{1, 2, 3}` 首先命中列表构造函数，构造函数随后把只读临时数组复制进 `vector`。指针使用 `nullptr` 初始化和比较，语义不会与整数重载混淆。

- 面向值对象的普通初始化优先使用花括号。
- 调用存在列表构造函数的容器或类时，先确认“元素列表”和“构造参数”含义。
- 泛型工厂常用圆括号完美转发，因为无条件改成花括号会改变重载选择。
- 接口的空指针默认值写 `nullptr`，不要写 `0` 或 `NULL`。
