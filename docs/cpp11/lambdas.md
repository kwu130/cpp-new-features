# Lambda 表达式

阅读前建议先了解：[迭代器与算法](../prerequisites.md#迭代器与算法)、[引用生命周期](../prerequisites.md#对象生命周期与引用)。本篇介绍的新增能力属于 C++11；后续版本差异会另行标注。

## 学习目标与前置知识

读者应先会普通函数、函数对象和 STL 算法。读完后，你应该能够写出 Lambda 的参数、返回类型和捕获列表，理解闭包对象的本质，并避免回调中的悬空引用和共享所有权环。

## C++03 中的问题

C++03 把一小段比较、过滤或回调逻辑交给算法时，通常要在远离调用位置的地方定义函数或函数对象类。代码阅读者需要来回寻找定义，函数对象若带状态还要手写构造函数和成员。

C++11 的 Lambda 表达式允许在使用位置创建匿名函数对象，使局部策略与调用代码放在一起。它仍然是静态类型对象，编译器可以像普通函数对象一样内联优化。

## 最小语法

```text
[captures](parameters) -> return_type {
    statements
}
```

捕获列表决定函数体如何访问外围自动变量：`[value]` 保存副本，`[&value]` 保存引用，`[]` 不捕获。返回类型简单时可省略尾置返回类型。

## 先看一个带捕获的 Lambda

传统写法把运算和状态放进函数对象类；Lambda 在使用位置表达同一逻辑。捕获就是让这段局部逻辑保存或访问外围变量。

```cpp example id="cpp11-lambda-capture-basic" std="c++11" file="main.cpp" kind="single" compilers="all" output="old=6, lambda=6, snapshot=6, current=15"
#include <iostream>

struct Multiply {
    int factor;
    int operator()(int value) const { return value * factor; }
};

int main() {
    int factor = 2;
    Multiply old_style{factor};
    auto snapshot = [factor](int value) { return value * factor; };
    auto current = [&factor](int value) { return value * factor; };
    std::cout << "old=" << old_style(3) << ", lambda=" << snapshot(3);
    factor = 5;
    std::cout << ", snapshot=" << snapshot(3) << ", current=" << current(3) << '\n';
}
```

按值捕获的 factor 是创建时的副本，按引用捕获的 factor 仍指向原变量，因此改变 factor 后得到不同结果。引用捕获不延长原变量寿命。局部算法和短回调适合 Lambda；复杂、需要命名复用的策略可以继续使用函数或类。闭包是编译器生成的函数对象，其布局没有标准保证。

## 组合示例：过滤与累加

第一个 Lambda 按值捕获阈值并过滤元素；第二个 Lambda 按引用捕获计数器，记录算法调用次数。

```cpp example id="cpp11-lambdas" std="c++11" file="main.cpp" kind="single" compilers="all" output="12"
#include <algorithm>
#include <iostream>
#include <numeric>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3, 4};
    const int threshold = 2;
    values.erase(std::remove_if(values.begin(), values.end(),
                                [threshold](int value) { return value < threshold; }),
                 values.end());

    int calls = 0;
    const int sum = std::accumulate(values.begin(), values.end(), 0,
                                    [&calls](int total, int value) {
                                        ++calls;
                                        return total + value;
                                    });
    std::cout << (sum + calls) << '\n';
}
```

程序输出 `12`：过滤后元素为 `2, 3, 4`，和为 9，累加器被调用 3 次。优先显式列出捕获项，避免 `[&]` 或 `[=]` 在长生命周期回调中意外捕获对象。按值捕获默认不可修改；需要维护内部状态时可使用 `mutable`，但它修改的是闭包内部副本。

## 底层模型：Lambda 会生成闭包类型

编译器会为每个 Lambda 表达式生成一个唯一、不可直接命名的闭包类，并把函数体变成 `operator()`。即使文本完全相同，两个 Lambda 表达式的闭包类型也不同。`auto` 能直接保存具体闭包类型，因此通常比 `std::function` 更轻量。

概念上，`[factor](int x) { return x * factor; }` 接近一个拥有 `factor` 数据成员和调用运算符的类。标准没有规定成员布局与名称，但允许编译器像优化普通类一样内联调用、消除未使用捕获。

无捕获 Lambda 可以转换为同签名函数指针；有捕获 Lambda 需要对象状态，不能进行这种转换。闭包的 `operator()` 默认是 `const`，所以按值捕获成员不可修改，`mutable` 会移除这一限制。

Lambda 语法由捕获列表、可选参数列表、可选 `mutable`、异常说明、尾置返回类型和函数体组成。无参数且不需要其他说明时可省略 `()`；一旦写 mutable/noexcept/返回类型，就要保留参数括号。

C++11 参数类型必须显式写出，`auto` 泛型参数是 C++14 特性。返回类型在简单情况下由 return 推导；多个 return 复杂情形可用 `-> ReturnType` 固定契约，避免不同分支推导冲突。

Lambda 不能有默认捕获同时显式重复同类捕获；`[&, x]` 表示默认引用但 x 按值，`[=, &x]` 反之。捕获只针对可达自动存储变量和 this 等规则允许实体，全局/静态变量无需捕获即可按普通名称访问。

### 异常说明

调用运算符可以声明 `noexcept`，使调用表达式参与 noexcept 检查并在异常逃出时终止。它不是“编译器自动证明不抛”，应只在函数体调用链满足契约时使用。

```cpp example id="cpp11-lambda-noexcept" std="c++11" file="main.cpp" kind="single" compilers="all" output="noexcept=true, value=42"
#include <iostream>

int main() {
    const auto twice = [](int value) noexcept -> int {
        return value * 2;
    };

    static_assert(noexcept(twice(21)), "lambda call must not throw");
    std::cout << std::boolalpha
              << "noexcept=" << noexcept(twice(21))
              << ", value=" << twice(21) << '\n';
}
```

转换为函数指针时异常说明的类型系统地位在后续标准有演进，跨版本回调签名需实际验证。C API 本身也不会理解 C++ 异常，回调边界应捕获异常而非让其跨语言传播。

## 捕获语义与生命周期

按值捕获在创建闭包时复制当前值，之后外围变量改变不影响副本。按引用捕获通常只保存能够访问原对象的引用语义；闭包不会延长对象生命周期。异步任务、事件循环和对象成员回调是悬空引用高发区域。

在成员函数中使用成员会捕获 `this` 指针，而不是分别复制每个成员。即使写 `[=]`，C++11 中仍是复制指针；对象销毁后回调访问成员会悬空。长期回调应考虑捕获拥有对象的 `shared_ptr` 或可检测失效的 `weak_ptr`，并审查可能形成的所有权环。

按值捕获发生在 Lambda 表达式求值时，使用捕获变量的当前值。捕获成员在闭包中的初始化顺序不应被用户依赖；表达式副作用应在外部先完成，避免捕获列表隐含顺序耦合。

按引用捕获 const 对象仍只能只读；mutable 只改变闭包 operator() 的 const，不移除所引用对象的 const。按值捕获 volatile/特殊对象也保留相应复制类型规则，闭包复制可能触发昂贵或受限构造。

不能直接捕获类数据成员名，成员函数中捕获 this 后访问成员。若只想保存成员快照，C++11 先复制到局部变量再按值捕获；C++14 初始化捕获能直接命名快照。

### 所有权环

对象把回调保存为成员，而回调捕获该对象 `shared_ptr`，会形成 `object -> callback -> shared_ptr<object>` 环。改捕获 `weak_ptr`，在调用时 lock 并处理对象已销毁，可打破环。

`weak_ptr` 方案会使回调可能什么也不做，接口应定义注销/失效语义。并发销毁时 lock 获得的 `shared_ptr` 保证此次调用期间对象存活，但对象内部线程安全仍需另外保证。

## 调用与性能模型

直接以模板参数接收 Lambda 时，编译器知道闭包具体类型，通常可以完全内联。存入 `std::function` 会进行类型擦除（通过统一接口保存和调用不同具体类型），可能引入间接调用和堆分配；具体是否分配取决于实现的小对象优化和闭包大小。

捕获大型对象会增大闭包，每次复制回调也会复制这些成员。可移动但不可复制的资源在 C++11 中较难直接捕获，C++14 初始化捕获解决了这一问题。

闭包大小通常至少容纳各按值捕获成员与对齐填充；引用捕获表示方式未规定，常见实现存指针。空闭包也必须有非零对象大小以保持不同对象地址。不能用捕获数量简单计算 sizeof。

模板算法直接接收闭包类型能内联，而虚接口/std::function 擦除后通常间接调用。若 Lambda 只调用一个大型非模板函数，可把重逻辑移出去，减少每个闭包实例代码膨胀。

算法可能复制/移动谓词的次数由接口和实现决定，副作用计数不能假定只存在一个闭包。副作用若是算法结果的一部分，应使用明确状态对象并在调用后从正确所有者读取。

## 示例解析与常见错误

主示例第一个 Lambda 按值捕获阈值，使谓词独立于后续变量修改；第二个按引用捕获计数器，让每次调用更新外围状态。算法可能复制谓词，因此不要依赖闭包副本之间共享的内部可变计数，除非共享状态是显式设计。

检查回调生命周期是否超过捕获对象；确认算法是否允许复制或并发调用回调；避免默认捕获掩盖真实依赖；高频路径测量 `std::function` 类型擦除成本。

## 无捕获 Lambda 与函数指针

无捕获 Lambda 可以隐式转换为具有匹配参数和返回类型的函数指针，这让现代局部写法能够传给旧式 C 回调接口。转换后的函数没有闭包对象状态；一旦捕获任何值，就不再具备这种转换。

带状态闭包则是普通对象。按值捕获的数据成员会随闭包复制，`mutable` 只允许非 const 调用运算符修改这些副本，不会修改外围原变量。

```cpp example id="cpp11-lambda-state-function-pointer" std="c++11" file="main.cpp" kind="single" compilers="all" output="callback=42, state=2, outside=0"
#include <iostream>

int call(int (*function)(int), int value) {
    return function(value);
}

int main() {
    const int callback = call([](int value) { return value * 2; }, 21);

    int outside = 0;
    auto counter = [outside]() mutable {
        return ++outside;
    };
    counter();
    const int state = counter();

    std::cout << "callback=" << callback
              << ", state=" << state
              << ", outside=" << outside << '\n';
}
```

## 闭包复制的工程含义

标准算法可以复制谓词，回调注册系统也可能保存多个副本。若状态必须在副本之间共享，应显式捕获 `shared_ptr<State>` 或引用一个生命周期受控的状态，而不是假设算法始终调用原闭包。反过来，独立副本正适合线程各自维护局部计数，避免不必要的同步。

闭包类型的复制/移动能力由捕获成员决定。C++11 捕获需要变量可按相应方式复制，无法用 `[p = move(p)]` 直接建立 move-only 闭包；可用命名函数对象或等到 C++14。

将 Lambda 暴露在公共 ABI（二进制接口约定，例如调用方式与对象布局） 中很困难，因为类型不可命名且每次重新编译实现可能变化。头文件模板可接受它，稳定边界通常用函数指针、std::function 或自定义接口类，并接受相应开销。

## 嵌套 Lambda 和捕获传播

内层 Lambda 若使用外层捕获成员，还需要按其自身捕获规则捕获相应实体。默认捕获并不会神奇地从最外层作用域拥有所有对象；每层闭包都有独立生命周期。

返回内层闭包时，若它按引用捕获外层调用运算符的局部/成员，外层调用结束后可能悬空。嵌套异步回调应逐层画出所有者和捕获边，尤其检查 this 与引用。

## 捕获与调用速查

| 形式 | 关键语义 |
| --- | --- |
| `[]` | 无捕获闭包，可转换为匹配函数指针 |
| `[=]` | 按需按值捕获局部实体，创建时形成快照 |
| `[&]` | 按需引用捕获，闭包不延长对象寿命 |
| `[x, &y]` | x 按值、y 按引用的显式组合 |
| `[this]` | 复制 this 指针，不拥有当前对象 |
| `mutable` | 允许修改按值捕获副本，operator() 不再默认 const |
| 尾置 `-> R` | 显式指定返回类型，适合多分支/转换 |
| 无捕获 + `+lambda` | 常用于强制函数指针转换，需匹配签名 |
| 闭包复制 | 复制捕获成员；引用捕获仍引用同一外部对象 |
| 并发调用 | 同一 mutable 闭包共享状态需要同步 |

## Lambda 专项审查

- 引用捕获目标是否覆盖闭包最后一次调用？
- `[this]` 是否在异步执行前对象已销毁？
- `[=]` 是否让读者误以为捕获了对象所有权？
- mutable 状态是否被多个线程并发修改？
- 闭包复制是否复制了意外昂贵的捕获对象？
- 无捕获转换函数指针的签名/noexcept 是否匹配？
- 返回类型多分支是否需要显式尾置类型？
- 异常从闭包构造还是调用阶段出现是否区分？
- 长期 API 是否不应暴露不稳定闭包 ABI 类型？
- 一次性局部逻辑是否已复杂到应命名函数对象？

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp11/lambdas.md
```

## 权威资料

- [Lambda 表达式](https://eel.is/c++draft/expr.prim.lambda)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
