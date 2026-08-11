# 可变参数模板与类型别名

可变参数模板允许模板接受任意数量的类型或值参数。别名模板用 `using` 为一族类型定义更易读的名称。

<!-- example id="cpp11-variadic-templates" std="c++11" file="main.cpp" kind="single" compilers="all" output="6" -->
```cpp
#include <iostream>
#include <memory>

template <typename T>
T sum(T value) {
    return value;
}

template <typename T, typename... Rest>
T sum(T first, Rest... rest) {
    return first + sum(rest...);
}

template <typename T>
using Owner = std::unique_ptr<T>;

int main() {
    Owner<int> result(new int(sum(1, 2, 3)));
    std::cout << *result << '\n';
}
```

C++11 中通常通过递归展开参数包，并提供终止重载。C++17 的折叠表达式会显著简化这种代码。参数包展开的上下文和求值顺序需要单独确认，不要假设函数实参按书写顺序求值。

## 参数包的组成

模板参数包 `typename... Types` 表示零个或多个模板参数，函数参数包 `Types... values` 表示由它们生成的一组函数参数。包本身不是运行期容器，不能索引；只有在带省略号的模式中才能展开。

若 `Types` 是 `int, double, string`，模式 `const Types&...` 会展开为三个独立参数。`sizeof...(Types)` 在编译期返回元素数量，不会生成遍历代码。

模板参数包必须位于模板形参列表允许的位置；函数模板中后续参数若可推导或有默认值可有更多组合，类模板参数包通常需位于末尾。函数参数包不等于 C varargs，它保留每个参数静态类型。

包可以是类型包、非类型包或模板模板参数包。一个展开模式可引用多个包，但同一次展开要求它们具有相同长度。没有内建 zip/truncate 行为，长度不符会在实例化时报错。

省略号位置决定展开模式：`f(values...)` 展开实参，`Base<Types>...` 展开基类，`std::tuple<Types...>` 展开模板实参，`sizeof...(Types)` 只是查询长度而不展开每个元素。

### 空包

空参数包合法，展开后产生空列表，并按所在语法判断最终结构是否合法。`tuple<>` 合法，函数调用 `f(args...)` 变成 `f()`；但继承列表、初始化列表技巧和递归重载仍需专门测试零元素。

递归 sum 主示例没有零参数终止重载，因此 `sum()` 不合法，这是可以接受的 API 决策。若数学上需要单位元，应显式提供 `sum()` 返回适当类型；没有类型信息时无法凭空选择通用零类型。

## 实例化模型

模板在使用点以具体实参实例化。主示例的 `sum(1, 2, 3)` 会形成多个不同签名的 `sum` 实例，每层处理一个参数并调用参数更少的实例，直到匹配单参数终止重载。优化器通常能内联这些层次，但模板实例数量仍会增加编译时间和目标文件体积。

包展开只是语法生成，求值顺序由展开所在语法决定。C++11 函数实参之间没有固定求值顺序；若展开项带副作用，应使用具有明确顺序的结构，或先消除副作用。

递归每层的返回类型也需要形成。主示例固定返回首参数 T，但 rest 中类型可以不同，递归结果会逐层转换回各层 T，可能窄化或选择意外 operator+。真正泛型求和应定义共同结果策略，而不是仅能编译就接受。

函数模板定义通常必须在实例化点可见。大量包实例放在公共头文件会让每个翻译单元重复解析/实例化，再由链接器合并弱 ODR 实体。显式实例化只能用于预先知道的有限类型组合。

错误往往在第 N 层递归暴露，实例化栈很长。把单元素操作抽成有名称的 helper，入口先断言长度/类型关系，可以让编译器指向更有意义的约束。

### 递归与继承展开

可变基类模式 `struct Overload : Fs...` 能组合函数对象，每个基类保存一种行为；C++11 需要额外 using 声明展开技巧才能汇集 operator()，标准库 tuple 也可能使用递归/多基类叶子存储。

继承展开会为每种类型生成基类子对象，重复基类、final 类型和构造顺序都要考虑。参数包只是生成结构，不会解决菱形继承或空基类 ABI 问题。

## 别名模板为何重要

传统 `typedef` 不能直接参数化，常需要额外包装结构体。`using Alias = ...` 的右侧从左到右更接近普通赋值写法，并能定义别名模板。别名不会创建新类型；`Owner<int>` 与 `std::unique_ptr<int>` 完全是同一类型，重载系统无法区分它们。

别名模板不能像类模板那样被部分/显式特化；要按类型条件选择别名，先特化一个辅助类模板，再用 alias 提取其 `type`。标准萃取 `_t` 别名在后续标准中正是这种包装便利。

依赖类型右侧仍可能需要 `typename`，依赖模板成员仍可能需要 `template` 消歧义。using 改善可读性，不取消两阶段名称查找规则。

别名可绑定复杂函数指针、allocator 重绑定和嵌套容器，但过多层 alias 会隐藏所有权和复杂度。公共 API 应让名称表达语义，并在文档给出最终类型约束。

### 可变参数别名

别名模板本身也能接收参数包，例如把 `tuple<Ts...>` 包装成领域记录，或为回调签名生成 `function<R(Args...)>`。每个使用点仍是原始模板特化，不产生运行时包装层。

如果需要对某些 Ts 拒绝实例化，可在底层类模板用 enable_if/static_assert；alias 声明本身没有函数重载式 SFINAE 接口。

## 递归边界与诊断

可变参数递归必须有可匹配终止条件，否则实例化会不断继续并产生很深的错误信息。还应考虑空参数包是否有业务含义：求和可选择返回单位元，也可通过约束禁止空调用。

终止重载必须在递归模板的名称查找/定义语境中可见。模板两阶段查找会让“稍后才声明”的普通重载不一定进入候选，推荐先声明终止版本，再定义递归版本。

重载过宽可能在终止点歧义。例如同时有单参数通用重载和可接收零个 Rest 的递归重载，二者都匹配。通过 `sizeof...(Rest)`、enable_if 或签名设计确保唯一递减路径。

模板递归深度不是运行时栈深度保证；优化器可能内联，但编译器前端仍实例化层次。大规模同质数据应使用运行时循环，参数包适合固定异构集合。

## 完美转发工厂

参数包与转发引用组合能把任意构造实参传给目标类型，是 make_unique、emplace 等接口的基础。每个参数必须用对应推导类型 forward，不能整体 move。

<!-- example id="cpp11-variadic-forwarding-factory" std="c++11" file="main.cpp" kind="single" compilers="all" output="Ada:37" -->
```cpp
#include <iostream>
#include <memory>
#include <string>
#include <utility>

template <typename T, typename... Args>
std::unique_ptr<T> make_owner(Args&&... args) {
    return std::unique_ptr<T>(new T(std::forward<Args>(args)...));
}

class Person {
public:
    Person(std::string name, int age)
        : name_(std::move(name)), age_(age) {}

    void print() const { std::cout << name_ << ':' << age_ << '\n'; }

private:
    std::string name_;
    int age_;
};

int main() {
    std::unique_ptr<Person> person = make_owner<Person>("Ada", 37);
    person->print();
}
```

Args 分别推导字符串字面量引用和 int，展开后的 forward 保留每个实参类别。C++14 标准 make_unique 提供同类功能；这里用于展示 C++11 参数包机制，不建议项目重复维护标准工厂。

花括号初始化列表没有普通可推导类型，完美转发工厂通常不能直接接 `{...}`；还要注意私有构造访问发生在工厂模板内部。参数包不消除这些语言边界。

## 工程实践

- 把复杂包展开封装在小型辅助函数中，公共接口保持直观。
- 对参数数量、类型关系用 `static_assert` 提前给出清晰诊断。
- 使用转发引用时才配合 `std::forward<Types>(values)...`。
- 关注编译时间和代码膨胀；对大量类型共享的逻辑移到非模板实现中。

## 有序展开参数包

C++11 函数实参求值顺序不能用于实现有副作用的左到右遍历。常见方案是把每一步放进初始化列表，因为初始化器元素按顺序求值。额外的首元素保证空参数包时数组仍有合法长度。

<!-- example id="cpp11-ordered-pack-expansion" std="c++11" file="main.cpp" kind="single" compilers="all" output="1 2 3" -->
```cpp
#include <iostream>

template <typename... Values>
void print_in_order(const Values&... values) {
    bool first = true;
    using Expansion = int[];
    (void)Expansion{0, ((std::cout << (first ? "" : " ") << values,
                         first = false), 0)...};
    std::cout << '\n';
}

int main() {
    print_in_order(1, 2, 3);
}
```

这个技巧依赖初始化列表的顺序保证，而不是依赖编译器碰巧从左到右计算函数参数。C++17 的逗号折叠表达式能更直接表达同一意图。

## 别名不是强类型

`using UserId = int` 只提供另一个拼写，不能阻止把订单编号传给用户编号接口。需要真正区分领域值时，应定义包装结构体并显式提供比较、哈希与转换。别名模板适合简化类型组合，不适合建立新的类型安全边界。

## 权威资料

- [可变参数模板](https://eel.is/c++draft/temp.variadic)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
