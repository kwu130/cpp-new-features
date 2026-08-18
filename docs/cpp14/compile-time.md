# 变量模板与放宽的 `constexpr`

## 学习目标与 C++11 的限制

C++11 `constexpr` 函数体通常只能用单个返回表达式，循环算法被迫改写成递归；模板可以定义一族类型或函数，却没有同样直接的“一族变量”语法。

C++14 放宽常量函数体，并加入变量模板。读完后，你应该能够用局部变量、条件和循环编写编译期算法，定义按类型参数实例化的常量，并理解它们在多翻译单元中的实体与链接边界。

## 最小语法

```text
template <typename T>
constexpr T zero = T{0};

constexpr int calculate(int input) {
    int result = 0;
    for (int i = 0; i < input; ++i) result += i;
    return result;
}
```

放宽的是函数体表达能力，不代表 C++14 的所有标准库容器都能在常量求值中使用，也不允许常量路径执行动态分配或 I/O。

## 第一个完整示例

示例用变量模板为不同类型提供零值，并用循环在编译期计算 1 到 10 的和。

```cpp example id="cpp14-compile-time" std="c++14" file="main.cpp" kind="single" compilers="all" output="55"
#include <iostream>
#include <type_traits>

template <typename T>
constexpr T zero = T{0};

constexpr int sum_to(int limit) {
    int result = 0;
    for (int value = 1; value <= limit; ++value) {
        result += value;
    }
    return result;
}

int main() {
    constexpr int result = sum_to(10) + zero<int>;
    static_assert(result == 55, "compile-time loop must work");
    static_assert(std::is_same<decltype(zero<long>), const long>::value,
                  "a constexpr variable is const");
    std::cout << result << '\n';
}
```

程序输出 `55`。`result` 的初始化和两个断言都要求常量求值成功。命名空间作用域变量模板仍可能涉及多翻译单元定义与地址身份问题；C++17 的内联变量才提供更直接的统一实体机制。

## C++14 放宽了什么

C++11 常量函数几乎只能包含单个返回表达式，复杂算法被迫改写成递归。C++14 允许局部变量、条件、循环以及对局部对象的修改，只要常量求值路径仍不执行被禁止操作。这样编译期算法可以采用与运行期版本相同的迭代结构。

放宽语法不意味着所有标准库容器都能在编译期使用。C++14 标准库中的许多成员函数尚未标为 `constexpr`，动态分配也受到限制；通常使用字面类型、固定数组和纯计算。

允许的函数体可包含普通声明、`if`/`switch`、循环以及对生命周期位于当前常量求值中的对象进行修改。`goto`、try block、静态/线程局部变量等仍不属于可执行常量路径。精确限制以对应标准规则为准。

函数可以包含某些常量求值时走不到的运行期代码，只要被强制求值的路径不执行禁止操作。但在 C++14 对 constexpr 函数定义本身仍有语法要求，不能把后续标准的进一步放宽倒推回来。

非构造 constexpr 成员函数在 C++14 不再因为 constexpr 自动带 const 成员限定，可定义修改当前常量求值对象的成员函数。是否能修改实际对象仍由对象的 const 性和求值上下文决定。

```cpp example id="cpp14-constexpr-mutable-value" std="c++14" file="main.cpp" kind="single" compilers="all" output="point=4,6"
#include <iostream>

struct Point {
    int x;
    int y;

    constexpr Point(int x_value, int y_value) : x(x_value), y(y_value) {}

    constexpr void translate(int dx, int dy) {
        x += dx;
        y += dy;
    }
};

constexpr Point moved_point() {
    Point point(1, 2);
    point.translate(3, 4);
    return point;
}

int main() {
    constexpr Point point = moved_point();
    static_assert(point.x == 4 && point.y == 6, "constexpr mutation failed");
    std::cout << "point=" << point.x << ',' << point.y << '\n';
}
```

修改只发生在常量求值器管理的局部 Point 上，最终结果成为 constexpr 对象。它不是在编译期间修改某个运行时全局地址；编译器计算出对象表示后用于初始化最终常量。

## 变量模板实例化

变量模板为每组模板实参产生一个变量实例。`zero<int>` 与 `zero<double>` 是不同实体，具有各自类型和地址。示例把它声明为 `constexpr`，因此每个实例都是相应类型的常量值。

头文件中的非内联变量定义要遵守单一定义规则。常量模板的链接属性和取地址行为较细致，跨翻译单元共享身份时应设计清楚；C++17 `inline` 变量使头文件定义更直接。

变量模板可以有偏特化和显式特化，用于按类型提供常量或策略对象。例如后续标准库 `_v` 辅助本质上把 `trait<T>::value` 暴露为变量模板。特化仍必须遵守模板与 ODR 规则。

模板实参既可以是类型，也可以包含 C++14 允许的非类型参数。`template<class T, std::size_t N> constexpr ...` 能为每个类型/尺寸生成独立实体，但每个组合都可能增加符号和编译工作。

变量模板不一定 constexpr，也能代表一族可变全局变量；这种设计会产生分散共享状态和初始化问题，通常不如函数或类静态封装。最常见、安全的用途是编译期常量。

### 类型、链接和地址身份

命名空间作用域 constexpr 变量默认带 const，链接规则与普通模板实例、显式特化和 odr-use 共同作用。仅用于常量表达式时编译器可不分配存储；取地址后则需要真实实体。

库若承诺 `&constant<T>` 在所有翻译单元是同一地址，C++14 必须专门设计定义策略，不能从“值相同”推断“对象身份相同”。C++17 inline constexpr variable 才让头文件统一实体模式更直接。

## 常量求值引擎

编译器前端以解释器方式执行 `sum_to(10)` 的局部变量更新和循环，并在完成后产生常量 55。若改用运行期 `limit`，相同函数可以生成普通机器码。是否预计算由上下文决定，而不是由函数声明单独决定。

编译期循环过大同样会消耗构建时间，并可能触发编译器步数限制。把查表、协议常量等稳定计算前移通常有价值；把大型业务任务硬塞进常量求值则可能拖慢增量构建。

常量求值失败与普通优化失败不同。初始化 constexpr 变量、非类型模板实参、数组界、case 标签或 `static_assert` 条件时，表达式必须合法常量求值，失败是编译错误；普通运行期调用即使没被折叠也合法。

求值器会诊断越界、除零、溢出等使常量表达式不成立的路径，因此能提前暴露部分错误。但函数在其他运行期输入上的未定义行为不会因有一个 `static_assert` 测试就被全面证明安全。

编译器有实现资源限制，深循环/递归可能报超出 constexpr 步数。提高编译选项上限只是权衡，算法复杂度和每翻译单元重复求值仍应优化。

## 字面类型与可用数据结构

C++14 常量求值主要围绕字面类型：具有适当 constexpr 构造/析构性质、成员也可用于常量表达式的类型。自定义小型值对象、原生数组和简单聚合是常见载体。

标准容器是否可用取决于其成员是否 constexpr 以及动态分配规则。`std::array` 的只读能力在不同标准版本逐步完善，但不能假定 C++20/23 的 constexpr vector 能力存在于 C++14。

设计跨版本库时可把核心算法写成对简单迭代器/固定存储操作，并按特性宏选择 constexpr 修饰。不要在文档宣称函数“编译期可用”却没有用最低标准实际 `static_assert` 验证。

## 工程实践

- 为编译期算法同时测试边界值和运行期调用。
- 保持函数无外部状态、无未定义行为且输入规模可控。
- 变量模板名称应表达单位与类型语义，避免制造大量隐式全局状态。
- 用 `static_assert` 验证关键结果，但不要把实现细节写成难以演进的断言。

常量算法应对最小值、最大合法值和非法边界分别测试。非法路径若需要运行时错误，在 constexpr 上下文可能通过抛出路径导致非常量；C++14 诊断能力有限，应保持错误点清晰。

头文件中的大 constexpr 计算会在多个翻译单元重复。可以将结果生成为数据文件、显式实例化，或在后续标准用 inline 变量统一。选择取决于结果是否需要按类型实例化。

运行时和编译时走同一函数并不自动保证性能相同。检查优化后的机器码，同时测量构建耗时，避免把启动优化转化成不可接受的开发反馈延迟。

## 迭代式编译期算法

C++14 允许 `constexpr` 函数包含局部变量、循环和条件分支，让欧几里得算法等逻辑不再依赖模板递归或函数递归。常量求值器按普通控制流执行，遇到不允许的操作才拒绝常量上下文。

```cpp example id="cpp14-constexpr-gcd" std="c++14" file="main.cpp" kind="single" compilers="all" output="gcd=6"
#include <iostream>

constexpr int greatest_common_divisor(int left, int right) {
    while (right != 0) {
        const int remainder = left % right;
        left = right;
        right = remainder;
    }
    return left;
}

int main() {
    constexpr int result = greatest_common_divisor(48, 18);
    static_assert(result == 6, "gcd must be evaluated correctly");
    std::cout << "gcd=" << result << '\n';
}
```

运行期输入可以调用同一函数。编译器只在强制常量上下文中必须解释执行；优化器也可能对普通调用做常量传播，但那属于优化，不改变语言语义。

## 变量模板的链接与地址

每个模板实参组合产生独立变量实例。只读取可内联替换的常量通常没有链接问题；一旦取地址或进行 ODR-use，就需要满足对应版本的定义与链接规则。C++17 内联变量简化了头文件中共享实体的定义，C++14 库仍应谨慎处理需要统一地址的变量模板。

## 进一步的语言边界

### 能力速查

| 能力 | C++14 语义 |
| --- | --- |
| constexpr 函数局部变量 | 允许，但实际常量路径必须满足常量表达式规则 |
| `if` / `switch` | 可用于编译期控制流，只有实际选中路径参与本次求值 |
| `for` / `while` | 可迭代修改局部状态，仍受编译器求值资源限制 |
| 局部对象修改 | 可修改本次常量求值中生命周期合适的对象 |
| 运行期调用 | 同一函数可生成普通运行时代码，不保证一定折叠 |
| 抛出路径 | 可写入函数体，但强制常量求值实际执行抛出会失败 |
| 变量模板 | 每组模板实参形成变量特化，可按值或按实体使用 |
| 部分特化 | 支持；歧义与偏序按模板特化规则诊断 |
| 地址身份 | C++14 头文件 constexpr 副本不能假定全程序唯一地址 |
| 失败位置 | 可能直到具体变量/函数特化实例化才诊断 |

### `constexpr` 成员函数的 const 变化

C++14 放宽后，constexpr 成员函数可以是修改对象的非 const 函数，只要调用发生在允许修改的常量求值对象上。`constexpr` 描述求值资格，不替代 cv 限定；是否能对 const 对象调用仍由函数签名决定。

同一成员函数在运行期调用时执行普通修改。值类型应同时用 `static_assert` 覆盖编译期路径，并用普通对象测试运行期副作用，不能因带 constexpr 就假定调用没有状态变化。

### 变量模板特化与实体身份

变量模板可以显式特化和部分特化，偏序规则与其他模板相同。特化甚至可能让不同 T 得到不同变量类型；公共数值常量通常显式保持统一的 `T` 类型更易使用。

每组模板实参对应一个实体。C++14 还没有 inline variable，头文件中的 constexpr 变量模板常表现为各翻译单元的内部链接副本：按值相等不代表地址相同。若需要程序级唯一地址，应采用 extern 声明加单一定义或函数局部静态对象。

变量模板初始化式中的错误可能到相应特化实际实例化才出现。测试应覆盖主模板、每个部分特化以及地址是否属于接口语义，不能只验证一个按值表达式。

## C++14 常量求值专项审查

- 循环是否保证终止且不会触及编译器求值上限？
- 修改对象是否属于当前允许的常量求值生命周期？
- constexpr 成员函数 const 限定是否准确？
- 运行期调用是否仍保持与编译期相同结果？
- 变量模板部分特化是否存在偏序歧义？
- 不同特化是否意外产生不同变量类型？
- 变量模板地址是否被误当作全程序唯一身份？
- 是否错误依赖 C++17 inline variable 语义？
- 初始化溢出/越界是否用 `static_assert` 覆盖？
- 构建成本是否随输入规模显著增长？

## 权威资料

- [N3652：放宽 constexpr](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3652.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
