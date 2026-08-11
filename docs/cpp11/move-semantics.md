# 移动语义与完美转发

右值引用让类型能够转移资源而非复制资源。`std::move` 表示对象可以被移动，`std::forward` 在转发函数中保留实参原有的值类别。

<!-- example id="cpp11-move-forward" std="c++11" file="main.cpp" kind="single" compilers="all" output="moved 3 values" -->
```cpp
#include <cstddef>
#include <iostream>
#include <utility>
#include <vector>

class Buffer {
public:
    Buffer(std::initializer_list<int> values) : values_(values) {}
    Buffer(Buffer&&) noexcept = default;
    Buffer& operator=(Buffer&&) noexcept = default;
    Buffer(const Buffer&) = delete;
    Buffer& operator=(const Buffer&) = delete;
    std::size_t size() const { return values_.size(); }

private:
    std::vector<int> values_;
};

template <typename T, typename... Args>
T make_value(Args&&... args) {
    return T(std::forward<Args>(args)...);
}

int main() {
    Buffer original = make_value<Buffer>(std::initializer_list<int>{1, 2, 3});
    Buffer destination = std::move(original);
    std::cout << "moved " << destination.size() << " values\n";
}
```

## 易错点

`std::move` 本身不移动任何数据，只进行类型转换；真正的转移发生在移动构造或移动赋值中。被移动对象仍然有效，但其值通常未指定，只适合销毁或重新赋值。资源所有者应遵循零法则或五法则。

## 从复制成本到所有权转移

C++03 中，按值返回大型容器或把临时对象放入容器，语言层面只能选择复制或依赖编译器优化。右值引用让重载能够识别“即将结束生命周期的对象”，从中接管指针、句柄等资源，并把源对象重置为可析构状态。

值类别描述表达式而非对象：具名变量表达式永远是左值，即使变量类型是 `T&&`。因此移动构造函数内部若要继续把某个成员向下移动，仍需显式使用 `std::move(member)`。

## 典型底层实现

以动态数组为例，复制通常需要分配新缓冲区并逐个复制元素，时间复杂度为 O(n)；移动通常只交换三个机器字大小的字段（起始地址、大小、容量），复杂度为 O(1)，然后把源对象指针清空。这只是典型实现，不是所有类型移动都廉价：内嵌数组、固定缓冲区或分配器不兼容时仍可能逐元素移动。

移动后的对象必须满足类型不变量且可以安全析构。标准库常说其状态“有效但未指定”，这不等于可以随意调用所有带前置条件的成员函数。

## 完美转发与引用折叠

当函数模板参数写成 `T&&` 且 `T` 参与推导时，它是转发引用。左值实参令 `T` 推导为 `U&`，经引用折叠得到 `U&`；右值实参令 `T` 为 `U`，最终得到 `U&&`。`std::forward<T>` 根据推导出的 `T` 恢复原始值类别。

折叠规则可以记为：只要任一侧是左值引用，结果就是左值引用；只有 `&&` 与 `&&` 组合仍是右值引用。

## 特殊成员生成与 `noexcept`

用户声明析构、复制或移动操作会影响编译器是否隐式生成其他特殊成员。资源类要么只用 RAII 成员遵循零法则，要么完整审视五个操作。标准容器扩容时常通过 `std::move_if_noexcept` 选择移动；若移动可能抛异常而复制可用，为保持强异常保证，容器可能退回复制。

## 工程检查清单

- 只在源对象确实不再需要时调用 `std::move`。
- 返回局部变量时通常直接 `return value;`，不要用 `std::move` 妨碍 NRVO。
- 移动操作应保持源和目标的不变量，并尽可能真实地标注 `noexcept`。
- 转发函数只对需要保持值类别的参数使用 `std::forward`，普通业务参数不必套用完美转发。

## 权威资料

- [引用与引用折叠](https://eel.is/c++draft/dcl.ref)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
