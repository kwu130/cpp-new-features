# 泛型 Lambda 与初始化捕获

泛型 Lambda 可以用 `auto` 声明参数，本质上生成带模板调用运算符的闭包。初始化捕获允许在捕获列表中创建成员，尤其适合把只移动对象交给回调。

<!-- example id="cpp14-lambdas" std="c++14" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <iostream>
#include <memory>

int main() {
    auto add = [](const auto& left, const auto& right) { return left + right; };
    std::unique_ptr<int> value(new int(40));
    auto calculate = [owned = std::move(value), add]() {
        return add(*owned, 2);
    };

    std::cout << calculate() << '\n';
}
```

初始化捕获的名称属于闭包对象，而不属于外围作用域。移动捕获会使闭包通常只能移动；若把它放入要求可复制目标的 C++14 `std::function`，会发生编译错误。

## 泛型 Lambda 的转换模型

C++11 Lambda 的参数类型固定，想对不同数值类型复用逻辑需要单独定义函数对象模板。C++14 允许参数写 `auto`，编译器把闭包的 `operator()` 生成为成员函数模板。每一种实参类型仍会产生独立实例，调用保持静态分派，并非把参数装进运行期“万能类型”。

多个 `auto` 参数彼此独立推导；若业务要求两者类型相同，C++14 只能在函数体中用 `static_assert` 检查，C++20 才能更自然地写 Concepts 约束。泛型 Lambda 同样参与模板实例化，错误信息、代码膨胀和隐式转换规则都应按模板代码理解。

参数中的 `auto` 可以配合 `const`、引用和转发引用规则：`const auto&` 接受任意只读对象而不复制，`auto&` 只接收左值，`auto&&` 在泛型 Lambda 中会按实参值类别推导，具有与函数模板转发引用相同的折叠行为。

<!-- example id="cpp14-generic-lambda-forwarding" std="c++14" file="main.cpp" kind="single" compilers="all" output="lvalue rvalue" -->
```cpp
#include <iostream>
#include <string>
#include <utility>

struct Category {
    const char* operator()(const std::string&) const { return "lvalue"; }
    const char* operator()(std::string&&) const { return "rvalue"; }
};

int main() {
    const auto invoke = [](auto&& function, auto&& argument) -> decltype(auto) {
        return std::forward<decltype(function)>(function)(
            std::forward<decltype(argument)>(argument));
    };

    std::string text = "cpp14";
    std::cout << invoke(Category{}, text) << ' '
              << invoke(Category{}, std::move(text)) << '\n';
}
```

`decltype(argument)` 分别是 `string&` 和 `string&&`，把它交给 `forward` 才能保留调用方值类别。如果 Lambda 体直接写 `function(argument)`，具名参数表达式始终是左值，第二次也会选择左值重载。

尾置 `decltype(auto)` 让被调函数的返回引用性质保持不变。若适配层希望返回拥有值，应改用普通 `auto` 或显式类型，避免无意把内部对象引用泄漏出去。

### 返回类型与 SFINAE 边界

未写尾置返回类型的泛型 Lambda 由函数体推导返回类型。某个实例中返回表达式不合法时，诊断可能发生在调用运算符实例化内部，而不总能像显式尾置 `decltype(expression)` 那样平滑参与 SFINAE。

C++14 的泛型适配器如果要进入复杂重载集，常把合法性表达式放进尾置返回类型，或提升为命名函数对象模板。Lambda 无法在 C++20 之前直接写模板参数列表和 requires-clause，声明层约束能力有限。

无捕获泛型 Lambda 不是一个单一普通函数，因此不能像固定签名无捕获 Lambda 那样直接无歧义转换成任意函数指针。转换涉及目标签名对应的调用运算符实例，工具链与上下文必须能确定具体类型。

## 初始化捕获的对象模型

`[name = expression]` 在闭包对象中创建一个由表达式初始化的成员，其类型由 `auto` 规则推导。外围作用域不需要存在同名变量。示例中的 `owned = std::move(value)` 把 `unique_ptr` 移入闭包，原指针随后为空。

闭包因此包含只移动成员，编译器隐式生成的复制构造被删除。把这种闭包交给线程通常可移动，但 C++14 `std::function` 要求目标可复制，不能直接保存。接口设计应明确回调需要复制、移动还是仅在调用期间借用。

初始化捕获还可用于规范化类型、预计算值或只捕获对象的某个成员，而不是整个 `this`。但表达式只在创建闭包时求值一次，不能把它误解成每次调用重新计算。

初始化捕获采用类似 `auto` 的推导，因此 `[x = array]` 通常发生数组到指针退化，[`x = std::ref(object)`] 保存 reference_wrapper，而 `[&x = object]` 明确建立引用捕获。要保留数组值应包装进 `std::array` 或命名结构体。

捕获成员的声明顺序和名称是未公开的闭包实现细节，不能通过布局假设序列化 Lambda。不同 Lambda 表达式产生不同闭包类型；捕获列表相同也不让二者可赋值。

初始化表达式按闭包构造发生并可能抛异常。若前面捕获已构造、后续捕获失败，已构造成员按正常对象规则销毁。复杂资源组合更适合先在外部形成一个完整 RAII 状态对象，再一次移动捕获。

### 移动捕获后的调用协议

移动捕获只保证闭包构造获得资源，不保证调用运算符只执行一次。若 Lambda 从捕获成员中再次 move，第一次后成员进入有效但未指定/空状态；第二次调用必须有定义策略，例如返回空、抛错或由接口禁止。

标准算法和任务框架可能复制函数对象。只移动闭包不能进入要求 CopyConstructible 的接口；把资源改成 shared_ptr 虽能满足复制，却改变独占语义。更好的办法常是选择支持 move-only callable 的队列或给任务定义命名所有权类型。

## 生命周期与并发

按引用初始化捕获仍不拥有对象；例如 `[&alias = object]` 只是闭包中的引用语义。异步执行前必须保证对象生命周期覆盖任务。按值捕获可减少悬空风险，但闭包副本之间各有状态；若多个副本需要共享同步状态，应显式捕获共享对象并设计线程安全。

按值捕获指针仍只是复制地址，不拥有所指对象；捕获 `this` 同理。C++14 尚不能写 `[*this]`，若需要对象快照可在初始化捕获中显式复制某个对象或值状态，并警惕多态切片。

闭包的 `operator()` 默认 const，使普通按值成员不能修改；`mutable` 去掉该 const 限制，但不提供互斥。多个线程同时调用同一个 mutable 闭包并修改捕获成员会数据竞争。复制闭包可得到独立状态，但捕获的 shared_ptr 指向对象仍共享。

引用捕获局部变量后把闭包返回，是典型悬空错误。泛型 Lambda 的模板化不会延长任何寿命；编译器通常也无法从类型上区分安全全局引用与已离开作用域的栈引用。

## 示例解析与实践

示例的 `add` 会为整数调用实例化对应调用运算符，`calculate` 则拥有原 `unique_ptr`。两层 Lambda 都可被内联，通常没有动态分配。代码审查时检查泛型参数是否过宽、捕获表达式是否有副作用、闭包是否需要复制，以及移动后的外围对象是否仍被误用。

## 同一闭包的多次模板实例化

泛型 Lambda 的闭包类型只有一个，但它的调用运算符是模板。用不同参数类型调用时，编译器分别推导并实例化 `operator()`。这与一个函数模板被多种类型调用的代码尺寸和重载行为相同。

返回类型仍由每次实例化单独推导，因此某个参数组合合法不代表所有组合都合法。操作符 `+` 对整数表示算术，对字符串表示拼接；Concepts 出现前，泛型 Lambda 很难在声明处直接表达这种语义约束。

<!-- example id="cpp14-generic-lambda-instances" std="c++14" file="main.cpp" kind="single" compilers="all" output="sum=42, text=cpp14" -->
```cpp
#include <iostream>
#include <string>

int main() {
    const auto combine = [](const auto& left, const auto& right) {
        return left + right;
    };

    const int sum = combine(20, 22);
    const std::string text = combine(std::string("cpp"), std::string("14"));
    std::cout << "sum=" << sum << ", text=" << text << '\n';
}
```

## `mutable` 与移动捕获

移动捕获只发生在闭包构造时。闭包的调用运算符默认 `const`，若要从捕获的 `unique_ptr` 再次转移所有权，需要 `mutable`。这种回调往往只能成功消费一次，接口必须说明重复调用后的行为。

异步 API 如果复制回调，会拒绝只移动闭包或改变消费语义。C++14 项目常让任务队列自身支持移动任务，而不是强制套进可复制的 `std::function`。

## 实例化和代码尺寸

每个不同参数类型组合会实例化一个调用运算符。`combine(int,int)`、`combine(long,long)`、`combine(string,string)` 都可能生成独立代码，即使源 Lambda 只有一处。优化器可合并等价机器码，但标准不保证。

在公共头文件中放置被大量类型调用的复杂泛型 Lambda，会把编译成本扩散到每个翻译单元。把重逻辑委托给少量非模板函数、让 Lambda 只做类型适配，可以兼顾局部表达力和构建规模。

错误诊断会显示匿名闭包类型，给 Lambda 变量取清晰名称并把内部关键操作拆成命名函数，能让错误栈更易读。若它已经拥有多段分派、状态机和复杂约束，命名函数对象通常比继续增长 Lambda 更合适。

## 参数推导与捕获细节

### 形式速查

| 形式 | 精确含义 |
| --- | --- |
| `[](auto x)` | operator() 的一个独立按值模板参数 |
| `[](auto& x)` | 只接受合适左值并保留其类型限定 |
| `[](const auto& x)` | 可绑定多类值，只读观察且可能延长临时到调用结束 |
| `[](auto&& x)` | 转发引用；需配合 `forward<decltype(x)>` |
| `[x = expr]` | 创建闭包时计算 expr，按推导类型保存成员 |
| `[&x = object]` | 捕获别名引用，不负责延长 object 生命周期 |
| `[p = move(ptr)]` | 把独占状态移入闭包，闭包可能因此不可复制 |
| `mutable` | 允许修改按值捕获成员，不修改外围原变量 |
| 多种实参类型 | 分别实例化 operator()，可能增加代码尺寸 |
| 转为 `std::function` | 固定一个签名并进行运行期类型擦除 |

每个 `auto` 形参分别发明模板参数，所以 `[](auto a, auto b)` 允许两者类型不同，并不等价于 `template<class T>(T,T)`。若要求同类型，C++14 可用 static_assert 或转发到带签名约束的命名辅助模板。

`auto&&` 形参是转发引用；具名形参表达式本身仍是左值，透明转发必须写 `std::forward<decltype(arg)>(arg)`。`const auto&` 只表达只读观察，不能保留右值类别。

初始化捕获的表达式在创建闭包时执行一次，异常也从任务提交/闭包构造位置抛出，而不是调用闭包时。`[x = expr]` 通常按值保存；`[&x = object]` 保存引用且不会延长被引用对象生命周期。

同一 Lambda 表达式创建的多个对象类型相同但捕获状态独立；两个文本相同的不同 Lambda 表达式仍是不同闭包类型。包装进 `std::function<R(Args...)>` 会固定一个签名并丢失多类型泛型调用能力。

## C++14 Lambda 专项审查

- 每个 auto 参数独立推导是否符合参数关系？
- auto&& 是否正确 forward 原值类别？
- 函数体替换失败是否会成为硬错误而非 SFINAE？
- 初始化捕获表达式的异常发生阶段是否明确？
- 引用初始化捕获目标是否持续存活？
- 移动捕获是否让闭包不可复制并影响容器接口？
- mutable 是否只修改副本且没有并发竞争？
- 同一闭包多种实参是否共享可变状态？
- std::function 是否不必要地固定单签名？
- operator() 特化数量是否造成构建与代码膨胀？

## 权威资料

- [N3649：泛型 Lambda](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3649.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
