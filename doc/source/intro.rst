
Introduction
=====================================

In a data analysis project, we frequently want to run many different tools on the same input data. Too often, this requires structuring the data uniquely for each tool. This makes it difficult not only to test multiple tools, but also to plug several different datasets into one analysis, because each connection structure must be defined manually.

To alleviate this challenge of linking data to tools, Portable Encapsulated Projects (PEP) standardizes the description of data collections, enabling both data providers and data users to communicate through the common interface. Practically, this means individuals who describe their projects using this format will immediately inherit both greater portability for analysis as well as greater access to external complementary data. This link operates around a simple, standard, extensible definition of a project, or a set of annotated sample data.