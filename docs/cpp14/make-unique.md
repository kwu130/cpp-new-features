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

## 分配、删除器与限制

`make_unique` 使用普通 `new` 和默认删除器，不能直接指定自定义删除器，也不能接管既有句柄。文件句柄、C API 资源、内存池对象等需要显式构造带删除器的 `unique_ptr`。

与 `make_shared` 不同，`make_unique` 没有控制块合并问题，典型情况下就是一次对象分配。返回值通过移动或复制消除转移所有权，不复制被管理对象。

## 示例解析与接口设计

示例把姓名和年龄直接转发给 `Person` 构造函数，调用方从创建完成起就持有唯一所有权。若工厂还需要验证、选择派生类型或返回失败，应封装成业务命名工厂，并决定失败使用异常还是 `optional/expected` 风格，而不是退回裸 `new`。

工程规则可以简单设为：普通独占对象默认 `make_unique`；动态数组优先容器；自定义删除、私有构造或特殊分配才采用专门工厂。
