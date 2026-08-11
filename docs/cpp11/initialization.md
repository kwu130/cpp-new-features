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

列表初始化还用于 `new T{...}`、函数实参、return、成员默认初始化和构造初始化列表，但每个语境的目标类型/重载规则不同。不能把花括号当成有独立普通类型的表达式。

`auto values = {1,2,3}` 在元素类型一致时推导 initializer_list<int>，而 `auto value{1}` 在 C++11/缺陷修正与后续规则存在历史细节。跨工具链风格指南通常避免用 auto+花括号表达单值，直接写目标类型最清楚。

空花括号对标量值初始化为零，对指针得到空指针，对类选择默认构造/列表规则。它比未初始化局部变量安全，但也可能掩盖“必须显式提供”的业务字段，应由强类型构造器保证不变量。

### 窄化的常量例外

整数常量表达式转更窄整数若值可表示，可以通过列表初始化；运行期 int 转窄类型即便当前值恰好可表示也被视为窄化。编译器看的是表达式类别和目标可表示范围，不做运行期证明。

浮点到浮点的窄化规则在标准版本和缺陷修正中有精细条件；工程上若精度变化是意图，显式 cast 并加范围测试。列表初始化检查不是通用数值安全库。

指针到 bool 之类转换在列表初始化中也应谨慎，编译器诊断随标准缺陷修正可能有差异。不要借 `{pointer}` 把“是否为空”隐藏为数据构造，显式比较 nullptr。

## `initializer_list` 的对象模型

编译器通常为花括号中的元素创建一个临时只读数组，`initializer_list` 只保存指向该数组的起始指针和长度。复制 `initializer_list` 不会复制元素；它仍然观察同一段临时存储。元素类型是 `const T`，因此不能从列表元素直接移动出只移动对象。

临时数组生命周期会延长到绑定的 `initializer_list` 对象生命周期，但把其指针保存到更长寿命对象中仍会悬空。构造函数应在调用期间复制所需内容，而不是长期保存 `begin()`。

initializer_list 对象本身轻量且按值传递合理，提供 `begin/end/size`。它观察 const 元素，因此容器从列表构造只能复制元素；`vector<unique_ptr<T>>{...}` 无法把临时 unique_ptr 从 const 数组移动出来。

所有元素必须能形成一个共同元素类型。混合 `{1, 2.0}` 不能按普通 initializer_list 自动推断为 double；目标类型明确时每个元素还要分别通过窄化检查。

底层数组元素按顺序初始化，某元素构造失败时已构造元素析构。函数在调用期间读取安全，但返回参数 initializer_list 或保存 begin 指针会悬空；复制列表对象也不获得所有权。

### 重载陷阱

列表构造候选只要可行，普通构造即使转换看起来更好也不会参与第二阶段。vector<int>{10,20} 与 `(10,20)` 的语义差异是 API 设计的一部分，不是解析偶然。

某些列表构造候选最终因元素窄化失败时，编译器也不会总是退回普通构造。结果可能直接不合法。给类增加 initializer_list 重载是源代码行为变更，需要回归所有花括号调用。

## `nullptr` 的类型原理

`nullptr` 的类型是 `std::nullptr_t`。它能隐式转换为任意指针或成员指针，却不会像整数 `0` 那样优先匹配整数重载。它不占用“特殊地址对象”；转换后的空指针表示仍由目标指针类型和平台 ABI 决定。

nullptr 可用于布尔条件的上下文转换，表示 false，但不能参与普通整数算术。`sizeof(nullptr)` 是 nullptr_t 对象大小，不代表所有指针大小，代码不应依赖。

模板推导 `f(nullptr)` 推导参数为 nullptr_t，不会自动推导成任意 T*；如果函数模板要求指针形参 `template<class T> f(T*)`，调用方可能需要显式 cast/模板参数或提供 nullptr_t 重载。

nullptr 也能转换为空成员指针。成员指针表示可能与普通数据指针完全不同，再次说明它是语言级空指针常量，不是整数地址零的 ABI 假设。

### `std::nullptr_t` 接口

需要专门处理“明确空”可重载 nullptr_t，但一般 API 用具体指针/智能指针更表达对象类型。转发层若要保持空值类型，可用 decltype(nullptr) 或 <cstddef> 的 std::nullptr_t。

可变参数 C 接口不会从 nullptr 的静态类型知道目标指针种类，传给 printf 等仍需匹配精确协议；类型安全函数接口才是 nullptr 消除重载歧义的主要范围。

## 示例解析与工程建议

示例的 `Points{1, 2, 3}` 首先命中列表构造函数，构造函数随后把只读临时数组复制进 `vector`。指针使用 `nullptr` 初始化和比较，语义不会与整数重载混淆。

- 面向值对象的普通初始化优先使用花括号。
- 调用存在列表构造函数的容器或类时，先确认“元素列表”和“构造参数”含义。
- 泛型工厂常用圆括号完美转发，因为无条件改成花括号会改变重载选择。
- 接口的空指针默认值写 `nullptr`，不要写 `0` 或 `NULL`。

## 列表构造函数的重载优先级

列表初始化的两阶段规则可能让看似更匹配的普通构造函数失去机会。第一阶段只用整个列表尝试 `initializer_list` 构造函数；只要存在可行候选，就不会进入普通构造函数阶段。这也是给成熟类型新增列表构造函数可能破坏源代码行为的原因。

空列表还有特殊性：若类型拥有默认构造函数，`T{}` 通常优先执行值初始化而不是把空列表传给 `initializer_list` 构造函数。阅读重载集合时必须结合完整初始化形式，而不是只数参数个数。

<!-- example id="cpp11-list-overload-nullptr" std="c++11" file="main.cpp" kind="single" compilers="all" output="list=2, pointer" -->
```cpp
#include <cstddef>
#include <initializer_list>
#include <iostream>

class Choice {
public:
    Choice(int, int) : selected_("pair") {}
    Choice(std::initializer_list<int> values)
        : selected_(values.size() == 2 ? "list=2" : "list") {}
    const char* selected() const { return selected_; }

private:
    const char* selected_;
};

const char* select(int) { return "integer"; }
const char* select(int*) { return "pointer"; }

int main() {
    const Choice choice{10, 20};
    std::cout << choice.selected() << ", " << select(nullptr) << '\n';
}
```

如果把 `choice{10, 20}` 改成 `choice(10, 20)`，结果将选择普通双整数构造函数。`select(nullptr)` 则只匹配指针方向；写 `select(0)` 会优先匹配整数重载。

## 聚合初始化与类演进

聚合对象可以按成员声明顺序用列表初始化。给聚合新增私有成员、虚函数或某些构造函数可能使它不再满足对应标准版本的聚合定义，从而让调用点失效。公共配置结构如果依赖聚合初始化，应把“保持聚合”视作源代码兼容承诺。

C++11 聚合定义比后续版本更严格，默认成员初始化器等特性可能影响聚合资格。阅读现代资料时不能把 C++20 聚合规则套回 C++11。最低标准编译测试是最可靠证据。

聚合省略的尾部成员按空列表初始化；成员声明顺序就是构造顺序。没有字段名提示，长配置列表易把同类型值调换，后续 C++20 指定初始化才改善调用点可读性。

基类参与聚合初始化的能力也在后续标准演进。C++11 公共数据载体若需要继承和复杂不变量，最好提供显式构造函数而不是依赖版本敏感聚合规则。

## 权威资料

- [列表初始化](https://eel.is/c++draft/dcl.init.list)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
