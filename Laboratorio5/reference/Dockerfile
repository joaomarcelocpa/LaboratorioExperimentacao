FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /w
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src ./src
RUN mvn -B -q package -DskipTests

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /w/target/semente.jar semente.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "semente.jar"]
