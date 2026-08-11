# `make_unique`

`make_unique` 补齐了 C++11 智能指针工厂：它直接构造对象并返回 `unique_ptr`，避免显式出现 `new`。

<!-- example id="cpp14-make-unique" std="c++14" file="main.cpp" kind="single" compilers="all" output="Ada:37" -->
```cpp
#include <iostream>
#include <memory>
#include <string>
#include <utility>

class Person {
public:
    Person(std::string name, int age) : name_(std::move(name)), age_(age) {}
    void print() const { std::cout << name_ << ':' << age_ << '\n'; }

private:
    std::string name_;
    int age_;
};

int main() {
    auto person = std::make_unique<Person>("Ada", 37);
    person->print();
}
```

一般对象优先使用 `make_unique`。只有需要自定义删除器、从既有裸指针接管所有权等场景才直接构造 `unique_ptr`。

## 为什么工厂函数更安全

`make_unique<T>(args...)` 分配一块适合 `T` 的存储，并把参数完美转发给构造函数，最终返回拥有对象的 `unique_ptr<T>`。调用点不重复类型，也不会暂时暴露裸指针。

在复杂函数调用中，显式 `unique_ptr<T>(new T(...))` 会把分配、构造和所有权包装写成多个表达式步骤。现代求值顺序规则不断改进，但工厂函数仍能从结构上把它们封装成一个完整操作，更容易审查异常安全。

## 数组重载

C++14 支持 `make_unique<T[]>(size)` 创建动态数组并进行值初始化，返回 `unique_ptr<T[]>`。已知界数组 `make_unique<T[N]>` 被删除，防止接口语义含糊。多数动态序列仍应优先使用 `vector`，因为它同时保存长度并提供迭代器。

标准接口实际上按 `T` 是否为数组分成三组：

- 非数组类型参与 `make_unique<T>(args...)`，参数被完美转发给 `T` 的构造函数；
- 未知界数组参与 `make_unique<T[]>(n)`，执行等价于 `new U[n]()` 的值初始化，其中 `U` 是元素类型；
- 已知界数组 `make_unique<T[N]>(...)` 被显式删除，调用会在编译期失败。

数组重载只接收元素数量，不接收逐元素构造参数。对类类型数组，它要求元素能够被无参初始化；若每个元素需要不同构造参数，应使用 `vector`、显式循环或更贴近业务含义的容器工厂。返回的 `unique_ptr<T[]>` 使用 `delete[]`，并提供下标运算符，但不记录长度，也不提供 `begin()`/`end()`。

<!-- example id="cpp14-make-unique-array" std="c++14" file="main.cpp" kind="single" compilers="all" output="size=4, sum=100" -->
```cpp
#include <cstddef>
#include <iostream>
#include <memory>

int main() {
    const std::size_t size = 4;
    auto values = std::make_unique<int[]>(size);

    for (std::size_t index = 0; index < size; ++index) {
        values[index] = static_cast<int>((index + 1) * 10);
    }

    int sum = 0;
    for (std::size_t index = 0; index < size; ++index) {
        sum += values[index];
    }

    std::cout << "size=" << size << ", sum=" << sum << '\n';
}
```

这里的 `int` 元素先被值初始化为零。随后显式赋值只是为了展示数组所有权与下标访问；`size` 必须由调用方另行保存。若把指针单独传递给其他函数，长度信息不会随之传播，这是动态数组重载相对 `vector` 的重要限制。

## 分配、删除器与限制

`make_unique` 使用普通 `new` 和默认删除器，不能直接指定自定义删除器，也不能接管既有句柄。文件句柄、C API 资源、内存池对象等需要显式构造带删除器的 `unique_ptr`。

与 `make_shared` 不同，`make_unique` 没有控制块合并问题，典型情况下就是一次对象分配。返回值通过移动或复制消除转移所有权，不复制被管理对象。

### 私有构造函数不是自动可见的

即使在类的静态成员函数中调用 `make_unique<T>`，真正执行 `T` 构造表达式的代码仍位于标准库模板内部；标准库模板不是 `T` 的友元，因此不能访问私有构造函数。常见做法有三种：让构造函数公开、在类内部使用 `unique_ptr<T>(new T(...))` 并立即封装，或者引入受控的令牌/派生辅助类型。选择时应优先保持不变量清晰，而不是为了机械遵守“永远不用 `new`”而破坏访问控制。

### 自定义删除器与特殊分配

`make_unique` 的返回类型固定使用 `default_delete<T>`，接口中没有删除器模板参数。以下资源不适合直接用它创建：

- 需要 `fclose`、`free`、操作系统句柄关闭函数的资源；
- 来自对象池、共享内存或特定 allocator 的对象；
- 必须携带额外释放上下文的 C API 句柄。

这些场景应把释放策略编码进 `unique_ptr<Resource, Deleter>` 的类型。删除器若包含状态，可能增加智能指针对象大小；无状态删除器通常可利用空基类优化。资源的创建函数最好直接返回最终的 RAII 类型，避免裸句柄在调用方停留。

## 异常安全与求值边界

若分配失败，`new` 抛出 `bad_alloc`；若对象构造函数抛出，已分配存储会被释放，调用方不会得到半构造的智能指针。成功返回后，所有权只存在于结果 `unique_ptr` 中。

工厂函数的价值并不只是缩短语法。它把“分配、构造、立即建立所有权”合并为一个抽象操作，调用点不再需要检查某个裸指针是否已经被接管。对于异常安全审查，这种结构比在复杂表达式里手动配对 `new` 和智能指针构造更容易证明。

不过，`make_unique` 只保证自身创建对象的过程安全，不会替调用方回滚其他副作用。构造参数在进入函数前仍需要求值；若多个参数会修改同一状态，就应先明确求值依赖并拆分语句。

## 示例解析与接口设计

示例把姓名和年龄直接转发给 `Person` 构造函数，调用方从创建完成起就持有唯一所有权。若工厂还需要验证、选择派生类型或返回失败，应封装成业务命名工厂，并决定失败使用异常还是 `optional/expected` 风格，而不是退回裸 `new`。

工程规则可以简单设为：普通独占对象默认 `make_unique`；动态数组优先容器；自定义删除、私有构造或特殊分配才采用专门工厂。

## 常用接口速查

`make_unique` 创建完成后，后续操作来自 `unique_ptr`：`get()` 只观察地址，`release()` 放弃所有权并返回裸指针，`reset()` 替换或销毁当前对象，`swap()` 交换所有权。最需要警惕的是 `release()`：它不会销毁对象，调用者必须立即把返回值交给另一个明确的所有者，否则会泄漏。

不要从同一个裸指针分别构造两个 `unique_ptr`，也不要对 `get()` 的结果调用 `delete`。工厂函数能减少这类错误，但所有权被手动拆出后，仍需遵守唯一所有权不变量。

## 权威资料

- [N3656：make_unique](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3656.htm)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
