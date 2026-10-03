# 阅读现代 C++ 前的基础知识

本页不要求模板元编程经验。它补充后续教程共同依赖的概念；已经熟悉某一节时可以直接跳过。示例使用 C++11，阅读顺序是 C++11 → C++14 → C++17 → C++20 → C++23。

## 对象生命周期与引用

对象只有在生命周期内才能按其类型正常使用。局部对象通常在离开作用域时析构；动态对象的寿命由管理它的代码决定。引用和指针提供访问途径，通常不负责让目标继续存活。

```cpp example id="basics-reference-lifetime" std="c++11" file="main.cpp" kind="single" compilers="all" output="value=7, copy=9"
#include <iostream>

int main() {
    int value = 3;
    int copy = value;
    int& alias = value;
    copy = 9;
    alias = 7;
    std::cout << "value=" << value << ", copy=" << copy << '\n';
}
```

`copy` 是独立对象，`alias` 是原对象的另一个访问名字，所以赋值影响不同。引用不能在目标销毁后继续使用。函数返回局部对象的引用、回调保存短寿命变量的引用，都可能产生悬空引用。

`const T&` 表示不能通过这条引用修改 `T`，并不自动延长所有被引用数据的寿命。直接绑定临时对象有特定的寿命延长规则，不能把它推广成“引用总能延长对象寿命”。[对象生命周期](https://eel.is/c++draft/basic.life)、[临时对象](https://eel.is/c++draft/class.temporary)

## 所有权与 RAII

所有权回答“谁负责最后释放资源”。资源可以是动态内存、文件、锁等。能访问资源，不代表拥有它；多个组件能读取一个对象，也不代表必须使用共享所有权。

RAII（Resource Acquisition Is Initialization）把资源管理绑定到对象：对象取得资源，析构时释放。离开作用域时，无论正常结束、提前返回还是异常栈展开，已经构造好的局部对象都会按规则析构。程序异常终止等情况不在这一保证内。

例如 `std::vector` 管理自己的元素存储，`std::unique_ptr` 管理独占的动态对象，`std::lock_guard` 管理锁。优先使用这些已有管理类型，而不是给每条路径手工补 `delete` 或解锁。RAII 是设计方法，并非 C++11 新语法；C++11 提供了更多支持它的标准设施。[析构函数](https://eel.is/c++draft/class.dtor)、[异常栈展开](https://eel.is/c++draft/except.ctor)

## 迭代器与算法

迭代器像一个访问元素的位置：`*it` 取得当前位置的元素，`++it` 前进。`begin()` 表示起点，`end()` 表示越过最后元素的位置；空范围中两者相等。`end()` 用于比较，不能解引用。

```cpp example id="basics-iterator-algorithm" std="c++11" file="main.cpp" kind="single" compilers="all" output="found=3"
#include <algorithm>
#include <iostream>
#include <vector>

int main() {
    const std::vector<int> values{1, 3, 5};
    const auto it = std::find(values.begin(), values.end(), 3);
    if (it != values.end()) {
        std::cout << "found=" << *it << '\n';
    }
}
```

`std::find` 接收半开区间 `[begin, end)`，找到元素时返回其位置，否则返回终点。算法负责处理元素，容器负责存储，迭代器连接二者。容器修改后，原来的迭代器可能失效，必须查相应操作的规则。

“迭代器类别”描述可执行的操作及其保证。例如前向迭代器支持多遍遍历，随机访问迭代器支持常数时间跳转。能遍历不代表能用于排序；`std::sort` 需要随机访问迭代器。[迭代器要求](https://eel.is/c++draft/iterator.requirements)、[算法区间](https://eel.is/c++draft/algorithms.requirements)

## 普通模板与类型推导

模板用一份代码表达一组类型相关的操作。函数模板中的 `T` 是待确定的类型；调用时，编译器根据实参推导模板参数。确定模板实参后，按需要生成并检查对应的具体声明或定义，这叫实例化。类型推导与实例化都发生在编译期。

```cpp example id="basics-template-deduction" std="c++11" file="main.cpp" kind="single" compilers="all" output="integer=6, floating=3"
#include <iostream>

template <typename T>
T twice(T value) {
    return value + value;
}

int main() {
    std::cout << "integer=" << twice(3)
              << ", floating=" << twice(1.5) << '\n';
}
```

两个调用分别推导出 `T = int` 与 `T = double`。参数写成 `T` 时通常按值接收；写成 `T&` 时绑定引用。引用、`const` 和数组会影响推导，后续在[类型推导](cpp11/type-deduction.md)与[完美转发](cpp11/move-semantics.md#完美转发与引用折叠)中逐步展开。

类模板也用类型参数生成具体类型，例如 `std::vector<int>`。C++17 的类模板实参推导才进一步允许在部分初始化场景省略类模板实参。[模板实例化](https://eel.is/c++draft/temp.inst)、[函数模板推导](https://eel.is/c++draft/temp.deduct.call)

## 值类别：先区分表达式的用途

值类别描述表达式，不是给对象贴上永久标签。它帮助编译器决定引用能否绑定、应选择哪个重载。

| 类别 | 直观理解 | 例子 |
| --- | --- | --- |
| lvalue（左值） | 指向可识别对象或函数的表达式 | 变量名 `value`、`*pointer` |
| prvalue（纯右值） | 用于计算值或初始化对象的表达式 | `42`、`std::string("text")` |
| xvalue（将亡值） | 仍指向对象，但可供移动等操作选择 | `std::move(value)` |

lvalue 与 xvalue 合称 glvalue，prvalue 与 xvalue 合称 rvalue。不要用“有名字/没名字”代替这些规则：具名的 `T&&` 参数在函数体中仍是左值表达式，`std::move` 的结果也并不保证对象马上销毁。

第一次阅读只需要知道：复制与移动的选择由表达式、重载和类型共同决定。详细机制请在学完移动示例后再阅读。[表达式值类别](https://eel.is/c++draft/basic.lval)

## 怎样运行本页示例

源码就是本文中的完整 `cpp` 围栏；无需寻找额外的 `.cpp` 文件。验证器会提取代码到临时目录，按元数据指定的标准编译，运行程序并核对输出：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/prerequisites.md
```

命令从仓库根目录执行。继续阅读 [C++11 入口](cpp11/README.md)；需要核对标准事实时使用[权威资料](official-sources.md)。
