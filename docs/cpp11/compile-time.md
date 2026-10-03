# `constexpr` 与 `static_assert`

阅读前建议先了解：[普通模板](../prerequisites.md#普通模板与类型推导)与 const；进阶部分需要[对象生命周期](../prerequisites.md#对象生命周期与引用)。本篇介绍的新增能力属于 C++11；后续版本差异会另行标注。

## 学习目标与前置知识

读者应理解 `const`、函数调用和编译错误。读完后，你应该能够区分 `const` 与 `constexpr`，编写符合 C++11 限制的常量函数，并用 `static_assert` 在编译期检查不变量。

## C++03 中的问题

C++03 的编译期常量能力分散在整型常量、枚举和模板技巧中。简单计算常要改写成模板元编程，错误信息难读，自定义值类型也很难直接参与常量表达式。

C++11 用 `constexpr` 表达“这个变量必须由常量表达式初始化”或“这个函数具备常量求值资格”，再用 `static_assert` 在翻译阶段验证条件。

## 最小语法

```text
constexpr int value = 42;
constexpr int square(int x) { return x * x; }
static_assert(square(2) == 4, "square must work");
```

`constexpr` 函数不保证每次都在编译期运行；只有实参和使用语境要求常量时，调用才必须成功常量求值。

## 先比较常量与函数计算

传统写法用枚举或整型常量保存已经算好的结果。constexpr 函数把计算本身写成普通函数，既可用于常量表达式，也可以接收运行期输入；static_assert 则把检查提前到编译阶段。

```cpp example id="cpp11-constexpr-basic-comparison" std="c++11" file="main.cpp" kind="single" compilers="all" output="old=49, constant=49, ordinary=49"
#include <iostream>

enum { old_square = 7 * 7 };
constexpr int square(int value) { return value * value; }
static_assert(square(7) == old_square, "the calculations agree");

int main() {
    constexpr int constant = square(7);
    int input = 7;
    int ordinary = square(input);
    std::cout << "old=" << old_square << ", constant=" << constant
              << ", ordinary=" << ordinary << '\n';
}
```

constant 和 static_assert 都要求常量求值成功；ordinary 的初始化不要求语言层面的常量表达式，优化器仍可能折叠为 49。观察最终机器码有没有函数调用，不能代替判断语义。适合在数组尺寸、固定配置、纯计算与编译期检查中使用；文件读取、I/O 和线程操作不适合放进常量求值路径。

## 综合示例：递归计算与断言

下面用 C++11 允许的单个返回表达式递归计算阶乘，并用编译期断言验证结果。

```cpp example id="cpp11-compile-time" std="c++11" file="main.cpp" kind="single" compilers="all" output="120"
#include <iostream>

constexpr unsigned factorial(unsigned value) {
    return value <= 1 ? 1 : value * factorial(value - 1);
}

int main() {
    constexpr unsigned result = factorial(5);
    static_assert(result == 120, "factorial must be evaluated correctly");
    int values[result == 120 ? 1 : -1] = {0};
    std::cout << (result + static_cast<unsigned>(values[0])) << '\n';
}
```

程序输出 `120`。`result` 必须在编译期得到值，`static_assert` 不生成运行时代码。C++11 的 `constexpr` 函数体限制严格，通常只能包含单个返回语句；后续标准逐步放宽。

## 常量表达式的作用

常量表达式可以参与数组边界、枚举值、非类型模板实参和 `static_assert`。把错误提前到编译期能够缩短反馈周期，也允许编译器预计算结果并把常量直接写入目标文件。

`constexpr` 变量必须由常量表达式初始化且隐含 `const`。`constexpr` 函数表示“具备常量求值资格”，不是“每次调用都发生在编译期”；当实参不是常量或调用上下文不要求常量时，它就是普通函数调用。

C++11 区分 core constant expression、integral constant expression 等语境要求。数组界、case 标签和非类型模板整数实参通常需要整型/枚举常量结果；constexpr 类对象可用于更广的常量初始化，但不代表能直接作为 C++11 任意非类型模板实参。

常量初始化还影响静态存储期对象的启动阶段：能常量初始化的对象在动态初始化之前建立值，可减少跨翻译单元初始化顺序风险。`constexpr` 不解决析构顺序，也不自动提供内联变量的跨单元统一定义语义。

取一个 constexpr 变量的地址会要求对象身份和存储，不能再只把它当编译器内部数字替换。命名空间作用域 const/constexpr 的链接规则、odr-use 和类静态成员定义需要按 C++11 精确处理。

## C++11 规则边界

C++11 的非构造 `constexpr` 函数体基本只能包含一条 `return`，因此循环通常写成递归和条件表达式。函数必须返回字面类型，常量求值路径不能执行未定义行为、调用非 `constexpr` 函数或访问不允许的可变状态。

`constexpr` 构造函数使自定义类型成为编译期值对象，但每个成员都必须被初始化，并受到字面类型规则约束。后续标准放宽了函数体、局部变量和标准库可用范围，阅读代码时要核对最低标准版本。

非构造 constexpr 函数通常不能返回 void，返回类型要是字面类型，函数体除少量允许声明外必须归结为单个 return。条件逻辑通常用 `?:`，重复计算用递归。递归深度和编译器 constexpr 深度限制因此比 C++14 循环写法更明显。

constexpr 非静态成员函数在 C++11 隐式具有 const 成员语义，适合观察编译期对象而非修改它。C++14 改变/放宽了相关规则，不能把 C++14 可变 constexpr 成员实现回写到 C++11。

构造函数体必须为空等限制促使所有成员通过初始化列表建立。基类、虚函数、析构和成员类型共同决定类是否为字面类型；仅给某个构造函数加 constexpr 不足以让任意类进入常量表达式。

### constexpr 不等于 `const`

const 只禁止经该名字修改对象，初始化值可以来自运行期；constexpr 变量必须在编译期得到常量值并隐含顶层 const。`const int n = read();` 不是数组常量边界，`constexpr int n = 4;` 才明确满足。

constexpr 函数参数本身不是 constexpr 变量；一次具体调用能否常量求值取决于实参和执行路径。函数体也不能用关键字声明“这个参数总是编译期”。C++20 consteval 可以要求普通调用点的立即调用产生常量表达式；立即函数上下文内的组合调用另有规则，见[C++20 编译期能力](../cpp20/compile-time.md)。

## 编译器求值模型

前端解释执行常量表达式，并监控是否违反常量求值规则。成功时产生一个编译期值；失败并不总是错误——若上下文不要求常量，编译器可以生成运行时代码。只有数组边界、`static_assert` 等强制常量上下文才必须诊断。

常量求值不保证零编译成本。复杂递归会消耗编译器时间、内存和递归深度；把大规模计算搬到编译期应测量整体构建成本。

常量求值器按抽象机规则检查有符号溢出、除零、越界、未定义移位等。若发生在必须常量的路径，表达式不是合法常量并产生诊断。这提供了一条额外错误检测路径，但不证明其他运行期输入没有未定义行为。

普通调用即使实参是字面常量，语言也不强制它在编译阶段执行；优化器可做 constant folding。观察执行时间、副作用或调试单步来判断“是否 constexpr”是不可靠的，只有使用在强制常量上下文才能证明。

递归 factorial 对很大输入会先遇到无符号回绕（它本身有定义但结果无意义）或求值深度限制。编译期函数仍需要输入域契约和上限检查。

## `static_assert` 的设计价值

`static_assert(condition, message)` 在模板实例化位置验证类型大小、对齐、能力或业务不变量。相比等待深层表达式失败，它能提供更靠近接口的错误。断言应描述要求和修复方向，不要只重复条件文本。

C++11 语法要求第二个字符串字面量消息；省略消息是 C++17 才加入。消息不会在运行期进入控制流，也不应依赖编译器按固定格式输出。把类型名/数值动态拼进消息在该版本不可行，诊断上下文通常会展示实例化实参。

模板内 `static_assert` 若条件依赖模板参数，会在具体实例化时检查；若条件完全非依赖且为 false，模板定义本身立即失败。想让某个兜底分支仅在实例化时诊断，常使用 `dependent_false` 萃取，而不是直接 `static_assert(false, ...)`。

断言适合平台假设（字节数、对齐）、模板能力和固定协议常量，不适合验证运行期用户输入。也不要断言编译器私有布局来“锁定”本未承诺的 ABI（二进制接口约定，例如调用方式与对象布局），除非该平台就是明确部署契约。

### 与 `integral_constant` 配合

`std::integral_constant<T, v>` 把编译期值包装成类型，`true_type`/`false_type` 是布尔特化别名。C++11 类型萃取继承这些类型，因此既能读取 `::value`，也能把类型对象用于标签分派。

这种“值进入类型”是 C++11 元编程桥梁，但每个值会形成不同类型/实例。普通 constexpr 数值计算不需要都提升成模板类型；只有重载选择、特化或类型结构需要时才使用。

## 示例解析与实践

示例的 `factorial(5)` 位于 `constexpr` 变量初始化中，强制编译期求值；随后 `static_assert` 再验证结果。普通运行期输入仍可以调用同一函数。实践中应让编译期函数保持纯粹、输入规模受控，并为关键边界增加静态断言。

## `constexpr` 构造函数与字面类型

自定义类型要进入常量表达式，必须满足对应版本的字面类型要求，并通过 `constexpr` 构造函数初始化所有成员。C++11 构造函数体限制很严，通常把计算放在成员初始化列表或其他 constexpr 函数中。

```cpp example id="cpp11-constexpr-value-object" std="c++11" file="main.cpp" kind="single" compilers="all" output="area=12"
#include <iostream>

class Rectangle {
public:
    constexpr Rectangle(int width, int height)
        : width_(width), height_(height) {}
    constexpr int area() const { return width_ * height_; }

private:
    int width_;
    int height_;
};

int main() {
    constexpr Rectangle rectangle(3, 4);
    static_assert(rectangle.area() == 12, "area is a compile-time invariant");
    std::cout << "area=" << rectangle.area() << '\n';
}
```

## 常量求值与运行时对象共用接口

同一个 `Rectangle::area()` 也能用于运行时构造的矩形。设计良好的 constexpr API 不需要维护两套算法；它只是避免在实现中使用当前标准不允许常量求值的操作。后续标准扩大允许范围时，接口通常无需改变。

接口共用不意味着错误处理完全共用。抛异常、I/O、动态分配等路径在 C++11 常量求值中不可执行；可用前置条件、返回状态值或让非法路径不成为常量表达式。运行期仍要提供可诊断策略。

constexpr 属于函数声明契约的一部分，声明和定义必须一致。模板/内联 constexpr 函数通常放头文件，以便每个使用点看到定义并执行常量求值。

## 编译期测试策略

用 `static_assert` 覆盖典型值、零值和边界值；再用运行期测试覆盖非常量输入和错误路径。只有静态测试会遗漏运行路径，只有运行测试则不能证明 API 真能用于 C++11 常量上下文。

测试编译命令必须显式 `-std=c++11`，否则后续标准放宽可能让违规 C++11 实现悄悄通过。本仓库元数据与验证器正是把最低标准绑定到每个示例。

## 编译期接口速查

| 设施 | C++11 作用 |
| --- | --- |
| `constexpr` 变量 | 必须由常量表达式初始化并为 const |
| `constexpr` 函数 | C++11 函数体限制严格，适合短小表达式 |
| 常量上下文调用 | 必须成功常量求值，否则程序不合法 |
| 普通上下文调用 | 可作为运行期函数执行 |
| `static_assert(cond,msg)` | 编译期验证，C++11 必须提供消息字符串 |
| 字面类型 | 决定对象能否参与若干常量表达式场景 |
| 构造函数 constexpr | 让值对象可在编译期建立，成员需满足规则 |
| 分支算法 | C++11 常用条件运算和递归，C++14 才大幅放宽循环 |
| 编译成本 | 计算前移会消耗编译器时间和求值资源 |
| 诊断用途 | 用静态断言检查布局、范围和模板不变量 |

## C++11 编译期专项审查

- constexpr 函数体是否只使用 C++11 允许的严格形式？
- 是否误把 C++14 循环/局部修改写进 C++11 示例？
- `static_assert` 消息是否足以定位失败不变量？
- 普通调用是否仍允许按运行期路径执行？
- 字面类型的每个成员/构造是否满足标准要求？
- 递归编译期算法是否有终止与深度边界？
- 整数常量计算是否可能溢出目标类型？
- 编译期与运行期实现是否产生相同业务结果？
- 大计算是否导致每个翻译单元重复构建开销？
- 最小、最大和零输入是否都有 `static_assert` 测试？

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp11/compile-time.md
```

## 权威资料

- [constexpr 与常量表达式](https://eel.is/c++draft/dcl.constexpr)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
