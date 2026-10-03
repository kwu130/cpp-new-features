# 移动语义与完美转发

阅读前建议先了解：[所有权与 RAII](../prerequisites.md#所有权与-raii)、[类设计](class-improvements.md)；完美转发部分在[参数包](templates.md)之后阅读。本篇介绍的新增能力属于 C++11；后续版本差异会另行标注。

## 学习目标与理解顺序

本文假设读者理解构造函数、析构函数、复制构造和动态资源。读完后，你应该能够解释右值引用、移动构造、`std::move`、引用折叠和 `std::forward` 之间的关系。

建议分两次阅读：第一次只掌握“源内容不再需要时，可以把资源转交出去”；第二次再学习值类别、转发引用和异常保证。std::move 不承诺源对象即将销毁。

## C++03 中的问题：昂贵但没有必要的复制

拥有动态数组、文件句柄或大型容器的对象在复制时必须申请新资源并复制内容。当源内容不再需要时，深复制后再释放原资源可能是一种浪费；此时才适合考虑转移资源。

C++11 增加右值引用 `T&&`，让重载解析能够识别可复用资源的表达式。类型可以提供移动构造和移动赋值，把指针或句柄转交给新对象，再把源对象重置为可析构状态。

## 三个工具的直观分工

- 移动构造/赋值负责真正转移资源；
- `std::move(object)` 把表达式转换成可选择移动重载的形式，本身不搬运数据；
- `std::forward<T>(value)` 用于按推导出的类型转发参数，保留调用者的左值/右值性质；学完参数包后再阅读这一部分。

## 先比较复制与移动

复制是另外建立一份内容，移动则允许目标接管源的资源。先看普通对象的两个构造重载，不需要参数包或转发工厂。

```cpp example id="cpp11-copy-move-basic" std="c++11" file="main.cpp" kind="single" compilers="all" output="copy move, copied=3, moved=3"
#include <cassert>
#include <iostream>
#include <utility>
#include <vector>

struct Buffer {
    std::vector<int> values;
    explicit Buffer(std::vector<int> input) : values(std::move(input)) {}
    Buffer(const Buffer& other) : values(other.values) { std::cout << "copy "; }
    Buffer(Buffer&& other) : values(std::move(other.values)) {
        std::cout << "move";
    }
};

int main() {
    Buffer original(std::vector<int>{1, 2, 3});
    static_cast<void>(std::move(original)); // 只转换表达式，没有构造目标
    assert(original.values.size() == 3);
    Buffer copied = original;             // 传统复制写法
    Buffer moved = std::move(original);    // 选择移动构造
    std::cout << ", copied=" << copied.values.size()
              << ", moved=" << moved.values.size() << '\n';
    original.values.clear();              // clear 没有“必须非空”的前置条件
    assert(original.values.empty());
}
```

输出中的 copy 与 move 来自实际调用的构造函数。std::move 单独出现时没有转移元素；构造 moved 时，Buffer 的移动构造才移动内部 vector。两个目标都有三个元素，但不检查源移动后的大小。成员容器管理内存，示例不手写 new/delete。教学构造还打印日志，因此不无条件承诺 noexcept；真实业务类型若可直接使用这些成员，通常应采用默认特殊成员。

## 适用场景与常见误区

当大型容器、独占资源或任务状态确实需要转交给新对象，且调用者不再依赖源内容时，可以使用移动。仍需保留源内容时应复制；整数等小值的移动通常不比复制更快。

std::move 本身只做转换，不保证一定调用移动构造：类型没有合适的移动重载、对象带 const 等情况可能选择复制。标准库对象除另有规定外，移动后是“有效但值未指定”，仍可执行满足前置条件的操作，例如查询 empty()、clear() 或重新赋值。不能不经检查就调用要求非空的 front()。

自定义类型的移动后契约由其接口定义；设计资源类型时应维持不变量并保证安全析构，不要把标准库的通用保证自动套到任意用户代码上。[标准库移动后状态](https://eel.is/c++draft/lib.types.movedfrom)

## 进一步理解：值类别与资源转移

C++03 中，按值返回大型容器或把临时对象放入容器，语言层面只能选择复制或依赖编译器优化。右值引用让重载能够识别“可供移动重载使用的表达式”，从中接管指针、句柄等资源，并把源对象重置为可析构状态。

值类别描述表达式而非对象：具名变量表达式永远是左值，即使变量类型是 `T&&`。因此移动构造函数内部若要继续把某个成员向下移动，仍需显式使用 `std::move(member)`。

C++11 值类别可分 lvalue、xvalue、prvalue；glvalue/rvalue 是组合类别。`std::move` 把表达式转换为 xvalue，告诉重载解析资源可复用；临时构造表达式通常是 prvalue。右值不等于“没有名字的对象”这种单一规则。

const 对象 `std::move` 后得到 const T&&，大多数移动构造接收 T&& 不能绑定，于是可能选择复制构造。给即将移动的局部无意义加 const 会阻止资源转移；移动不应通过 `const_cast` 破坏契约。

标量 int 的“移动”与复制效果相同，用户类型也可能选择移动等价复制。移动语义提供重载机会，不保证任何类型 O(1) 或源必为空。

### 源对象状态

自定义移动应把源置于满足所有类不变量、可析构、可赋新值的状态。若文档承诺更多（如 `unique_ptr` 移动后为空），调用方可依赖；“有效但未指定”时，可以执行无前置条件操作，以及已确认前置条件成立的操作。

自移动赋值 `x = std::move(x)` 可能由泛型算法/交换路径出现。标准库类型有相应有效状态保证边界，自定义类型可显式 `if (this != &other)` 或设计 swap/成员操作使自移动安全，至少不能双释放。

## 典型底层实现

以动态数组为例，复制通常需要分配新缓冲区并逐个复制元素，时间复杂度为 O(n)；移动通常只交换三个机器字大小的字段（起始地址、大小、容量），复杂度为 O(1)，然后把源对象指针清空。这只是典型实现，不是所有类型移动都廉价：内嵌数组、固定缓冲区或分配器不兼容时仍可能逐元素移动。

移动后的对象必须满足类型不变量且可以安全析构。标准库常说其状态“有效但未指定”，这不等于可以随意调用所有带前置条件的成员函数。

移动赋值还必须先处理目标已有资源：释放、swap 或通过临时移动后交换。只覆盖目标指针会泄漏。异常发生时源/目标保持何种状态取决于操作顺序和保证。

小字符串优化使 string 的短内容存储在对象内部，移动短字符串可能复制字符；allocator 不相等且不可传播时容器移动赋值可能逐元素移动。测量具体场景，不把类型名等同成本。

### `swap` 实现策略

资源类常用 move 构造/赋值实现 swap，或反过来用成员 swap 实现移动赋值。需要避免递归调用，并让 noexcept 条件跟随成员 swap。Copy-and-swap 强保证会额外创建临时，move-aware 版本可降低成本。

标准 `std::swap` 默认使用移动构造和移动赋值；可为用户类型提供成员 swap 和同命名空间非成员 swap，让泛型代码通过 `using std::swap; swap(a,b);` 使用 ADL（实参依赖查找，从实参类型关联的命名空间中寻找候选）。不要非法特化通用算法来绕过。

## 转发引用的重载验证

完美转发的目标不是“总是移动”，而是让下游函数看到调用者原本提供的值类别。模板形参推导、引用折叠与 `std::forward` 三者缺一不可。若在转发函数中直接使用具名参数，它是左值表达式，右值信息会丢失。

```cpp example id="cpp11-perfect-forwarding-categories" std="c++11" file="main.cpp" kind="single" compilers="all" output="lvalue rvalue"
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

## 完美转发与引用折叠

本节在[参数包](templates.md)之后阅读。完美转发用于包装一层函数调用，同时保持实参原来的引用性质；它的目标不是“总是移动”。

当函数模板参数写成 `T&&`，且 T 是当前函数模板参与推导的 cv 未限定类型参数时，它是转发引用。cv 指 const/volatile 限定；引用折叠是将推导中叠加的引用合并成一个合法引用类型。左值实参令 `T` 推导为 `U&`，经引用折叠得到 `U&`；右值实参令 `T` 为 `U`，最终得到 `U&&`。`std::forward<T>` 根据推导出的 `T` 恢复原始值类别。

折叠规则可以记为：只要任一侧是左值引用，结果就是左值引用；只有 `&&` 与 `&&` 组合仍是右值引用。

转发引用要求 T 是当前函数模板直接推导的 cv 未限定模板参数。`const T&&` 不是转发引用，类模板中的 `T&&` 若 T 已由类特化固定也不是。auto&& 在相应推导语境遵循类似规则（`initializer_list` 有例外）。

`std::forward<T>(value)` 本质上按 T 做条件 cast；写错 T 可以强行把左值转成右值。始终使用该参数对应的推导模板形参，不要 `forward<U>` 猜测目标类型。

同一转发参数 forward 多次可能让下游第一次已移动资源，第二次观察移后状态。完美转发适合把参数消费一次；需要多次使用就先决定拥有/复制策略。

### 转发构造函数抢占

类中无约束 `template<class T> Wrapper(T&&)` 可能比复制构造更匹配非 const Wrapper 左值，导致模板递归或错误语义。C++11 常用 `enable_if` 排除 Wrapper 自身及不适合类型。

完美转发扩展可接受输入集合，explicit 转换也可能参与内部直接初始化。工厂/容器接口要权衡便利与诊断，不应给每个业务构造都加万能引用。

## 特殊成员生成与 `noexcept`

用户声明析构、复制或移动操作会影响编译器是否隐式生成其他特殊成员。资源类要么只用 RAII（把资源释放绑定到管理对象的析构） 成员遵循零法则，要么完整审视五个操作。标准容器扩容时常通过 `std::move_if_noexcept` 选择移动；若移动可能抛异常而复制可用，为保持强异常保证，容器可能退回复制。

默认移动逐基类/成员移动，数组成员逐元素移动；某个成员不可移动时可能退回其复制或使外层操作删除，取决于可用候选。显式 `= default` 仍会执行这些检查。

移动构造通常能 noexcept，移动赋值若要释放旧资源也常能通过不抛删除/swap做到。文件关闭等可能失败的资源需把错误报告从析构/移动路径分离，避免虚假 noexcept。

返回局部变量直接 `return value;` 可先尝试 NRVO，未省略时语言再选择移动。显式 `std::move(value)` 会让表达式不再满足常见 NRVO 形式，通常是悲观优化。

## 移动与继承

多态基类按值移动可能发生切片；接口通常通过 `unique_ptr<Base>` 转移对象所有权，而不是移动 Base 子对象。虚 clone 用于多态复制，与移动所有权是不同操作。

派生默认移动先移动基类再移动成员。基类用户声明虚析构可能抑制隐式移动，派生性能因此受影响；多态层级应明确是身份不可移动、指针可移动，还是值语义 clone。

protected/private 移动构造会影响容器和工厂可用性。访问控制错误不会因 std::move 绕过，move 只是转换。

## 工程检查清单

- 只在源对象确实不再需要时调用 `std::move`。
- 返回局部变量时通常直接 `return value;`，不要用 `std::move` 妨碍 NRVO。
- 移动操作应保持源和目标的不变量，并尽可能真实地标注 `noexcept`。
- 转发函数只对需要保持值类别的参数使用 `std::forward`，普通业务参数不必套用完美转发。

## 综合示例：转发工厂与移动

`Buffer` 禁止复制但允许移动。工厂用完美转发构造对象，随后把 `original` 的资源移动到 `destination`。

```cpp example id="cpp11-move-forward" std="c++11" file="main.cpp" kind="single" compilers="all" output="moved 3 values"
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

程序输出 `moved 3 values`。移动后只使用 `destination` 的内容；`original` 仍然可以析构或重新赋值，但除非类型另有保证，不应假定它还保存原来的三个元素。

## `move_if_noexcept` 与容器强保证

容器扩容要先在新存储中构造元素。如果移动中途抛异常且已经改变源元素，回滚旧容器会非常困难。标准库可以在“移动可能抛、复制可用”时选择复制，在移动不抛或对象只能移动时选择移动。

```cpp example id="cpp11-move-if-noexcept" std="c++11" file="main.cpp" kind="single" compilers="all" output="copy selected"
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

## 移动与转发速查

| 操作 | 精确含义 |
| --- | --- |
| `std::move(x)` | 无条件转换为右值类别，不实际搬运资源 |
| 移动构造 | 从右值建立新对象，源状态依类型契约；标准库通常保证有效 |
| 移动赋值 | 替换既有目标资源，需处理自移动与异常保证 |
| `T&&` 非推导位置 | 普通右值引用，不是转发引用 |
| `T&&` 推导形参 | T 可推为引用并发生引用折叠 |
| `std::forward<T>(x)` | 仅在 T 来自转发推导时恢复原值类别 |
| `const T&&` | 通常不能移动需修改的资源，少用于转发 |
| `move_if_noexcept` | 在复制可用且移动可能抛时可能选择复制 |
| moved-from 对象 | 标准库通常有效但值未指定；满足前置条件的操作可用 |
| 返回局部变量 | 通常直接返回，让隐式移动/消除生效，勿机械 move |

## 移动语义专项审查

- std::move 后是否仍依赖源对象的未承诺值？
- 资源类移动构造是否让源保持可析构/可赋值？
- 移动赋值是否正确释放目标旧资源？
- 自移动赋值是否保持有效状态或被接口禁止？
- noexcept 是否让容器重分配选择移动而非复制？
- 完美转发是否只对推导的 T&& 使用 std::forward？
- 具名右值引用是否被误当作右值表达式？
- const 对象是否无法调用需要修改源的移动构造？
- 返回局部是否被多余 move 阻碍复制消除？
- 移动性能是否真实优于复制而非仅名字如此？

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp11/move-semantics.md
```

## 权威资料

- [移动后状态](https://eel.is/c++draft/lib.types.movedfrom)
- [引用与引用折叠](https://eel.is/c++draft/dcl.ref)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
