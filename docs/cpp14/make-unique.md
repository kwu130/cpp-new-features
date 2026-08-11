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

