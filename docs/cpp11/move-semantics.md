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

C++11 值类别可分 lvalue、xvalue、prvalue；glvalue/rvalue 是组合类别。`std::move` 把表达式转换为 xvalue，告诉重载解析资源可复用；临时构造表达式通常是 prvalue。右值不等于“没有名字的对象”这种单一规则。

const 对象 `std::move` 后得到 const T&&，大多数移动构造接收 T&& 不能绑定，于是可能选择复制构造。给即将移动的局部无意义加 const 会阻止资源转移；移动不应通过 const_cast 破坏契约。

标量 int 的“移动”与复制效果相同，用户类型也可能选择移动等价复制。移动语义提供重载机会，不保证任何类型 O(1) 或源必为空。

### 源对象状态

自定义移动应把源置于满足所有类不变量、可析构、可赋新值的状态。若文档承诺更多（如 unique_ptr 移动后为空），调用方可依赖；只有“有效但未指定”时只能执行无额外前置条件操作。

自移动赋值 `x = std::move(x)` 可能由泛型算法/交换路径出现。标准库类型有相应有效状态保证边界，自定义类型可显式 `if (this != &other)` 或设计 swap/成员操作使自移动安全，至少不能双释放。

## 典型底层实现

以动态数组为例，复制通常需要分配新缓冲区并逐个复制元素，时间复杂度为 O(n)；移动通常只交换三个机器字大小的字段（起始地址、大小、容量），复杂度为 O(1)，然后把源对象指针清空。这只是典型实现，不是所有类型移动都廉价：内嵌数组、固定缓冲区或分配器不兼容时仍可能逐元素移动。

移动后的对象必须满足类型不变量且可以安全析构。标准库常说其状态“有效但未指定”，这不等于可以随意调用所有带前置条件的成员函数。

移动赋值还必须先处理目标已有资源：释放、swap 或通过临时移动后交换。只覆盖目标指针会泄漏。异常发生时源/目标保持何种状态取决于操作顺序和保证。

小字符串优化使 string 的短内容存储在对象内部，移动短字符串可能复制字符；allocator 不相等且不可传播时容器移动赋值可能逐元素移动。测量具体场景，不把类型名等同成本。

### `swap` 实现策略

资源类常用 move 构造/赋值实现 swap，或反过来用成员 swap 实现移动赋值。需要避免递归调用，并让 noexcept 条件跟随成员 swap。Copy-and-swap 强保证会额外创建临时，move-aware 版本可降低成本。

标准 `std::swap` 默认使用移动构造和移动赋值；可为用户类型提供成员 swap 和同命名空间非成员 swap，让泛型代码通过 `using std::swap; swap(a,b);` 使用 ADL。不要非法特化通用算法来绕过。

## 完美转发与引用折叠

当函数模板参数写成 `T&&` 且 `T` 参与推导时，它是转发引用。左值实参令 `T` 推导为 `U&`，经引用折叠得到 `U&`；右值实参令 `T` 为 `U`，最终得到 `U&&`。`std::forward<T>` 根据推导出的 `T` 恢复原始值类别。

折叠规则可以记为：只要任一侧是左值引用，结果就是左值引用；只有 `&&` 与 `&&` 组合仍是右值引用。

转发引用要求 T 是当前函数模板直接推导的 cv 未限定模板参数。`const T&&` 不是转发引用，类模板中的 `T&&` 若 T 已由类特化固定也不是。auto&& 在相应推导语境遵循类似规则（initializer_list 有例外）。

`std::forward<T>(value)` 本质上按 T 做条件 cast；写错 T 可以强行把左值转成右值。始终使用该参数对应的推导模板形参，不要 `forward<U>` 猜测目标类型。

同一转发参数 forward 多次可能让下游第一次已移动资源，第二次观察移后状态。完美转发适合把参数消费一次；需要多次使用就先决定拥有/复制策略。

### 转发构造函数抢占

类中无约束 `template<class T> Wrapper(T&&)` 可能比复制构造更匹配非 const Wrapper 左值，导致模板递归或错误语义。C++11 常用 enable_if 排除 Wrapper 自身及不适合类型。

完美转发扩展可接受输入集合，explicit 转换也可能参与内部直接初始化。工厂/容器接口要权衡便利与诊断，不应给每个业务构造都加万能引用。

## 特殊成员生成与 `noexcept`

用户声明析构、复制或移动操作会影响编译器是否隐式生成其他特殊成员。资源类要么只用 RAII 成员遵循零法则，要么完整审视五个操作。标准容器扩容时常通过 `std::move_if_noexcept` 选择移动；若移动可能抛异常而复制可用，为保持强异常保证，容器可能退回复制。

默认移动逐基类/成员移动，数组成员逐元素移动；某个成员不可移动时可能退回其复制或使外层操作删除，取决于可用候选。显式 `= default` 仍会执行这些检查。

移动构造通常能 noexcept，移动赋值若要释放旧资源也常能通过不抛删除/swap做到。文件关闭等可能失败的资源需把错误报告从析构/移动路径分离，避免虚假 noexcept。

返回局部变量直接 `return value;` 可先尝试 NRVO，未省略时语言再选择移动。显式 `std::move(value)` 会让表达式不再满足常见 NRVO 形式，通常是悲观优化。

## 移动与继承

多态基类按值移动可能发生切片；接口通常通过 unique_ptr<Base> 转移对象所有权，而不是移动 Base 子对象。虚 clone 用于多态复制，与移动所有权是不同操作。

派生默认移动先移动基类再移动成员。基类用户声明虚析构可能抑制隐式移动，派生性能因此受影响；多态层级应明确是身份不可移动、指针可移动，还是值语义 clone。

protected/private 移动构造会影响容器和工厂可用性。访问控制错误不会因 std::move 绕过，move 只是转换。

## 工程检查清单

- 只在源对象确实不再需要时调用 `std::move`。
- 返回局部变量时通常直接 `return value;`，不要用 `std::move` 妨碍 NRVO。
- 移动操作应保持源和目标的不变量，并尽可能真实地标注 `noexcept`。
- 转发函数只对需要保持值类别的参数使用 `std::forward`，普通业务参数不必套用完美转发。

## 转发引用的重载验证

完美转发的目标不是“总是移动”，而是让下游函数看到调用者原本提供的值类别。模板形参推导、引用折叠与 `std::forward` 三者缺一不可。若在转发函数中直接使用具名参数，它是左值表达式，右值信息会丢失。

<!-- example id="cpp11-perfect-forwarding-categories" std="c++11" file="main.cpp" kind="single" compilers="all" output="lvalue rvalue" -->
```cpp
#include <iostream>
#include <string>
#include <utility>

void category(const std::string&) { std::cout << "lvalue"; }
void category(std::string&&) { std::cout << "rvalue"; }

template <typename T>
void relay(T&& value) {
    category(std::forward<T>(value));
}

int main() {
    std::string text = "data";
    relay(text);
    std::cout << ' ';
    relay(std::string("temporary"));
    std::cout << '\n';
}
```

第一次调用中 T 推导为 `std::string&`，折叠后参数是左值引用；第二次 T 为 `std::string`，参数是右值引用。`forward<T>` 根据这个 T 有条件地转回右值。

## `move_if_noexcept` 与容器强保证

容器扩容要先在新存储中构造元素。如果移动中途抛异常且已经改变源元素，回滚旧容器会非常困难。标准库可以在“移动可能抛、复制可用”时选择复制，在移动不抛或对象只能移动时选择移动。

<!-- example id="cpp11-move-if-noexcept" std="c++11" file="main.cpp" kind="single" compilers="all" output="copy selected" -->
```cpp
#include <iostream>
#include <type_traits>
#include <utility>

struct Value {
    Value() {}
    Value(const Value&) {}
    Value(Value&&) noexcept(false) {}
};

int main() {
    Value value;
    typedef decltype(std::move_if_noexcept(value)) Selected;
    static_assert(std::is_same<Selected, const Value&>::value,
                  "copy path is selected when move may throw");
    std::cout << "copy selected\n";
}
```

这不意味着所有容器实现都必须在每个操作中调用名为 `move_if_noexcept` 的函数，而是说明标准库常用的类型级决策。为真实不抛移动构造标注 `noexcept`，能让容器采用更高效且仍满足异常保证的路径。

## 权威资料

- [引用与引用折叠](https://eel.is/c++draft/dcl.ref)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
