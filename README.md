# VModel
Blender exporter for the vmodel file format.

It's primary use at the moment is for allowing models to be exported from Blender into the Biome Defense game project at runtime. (project thread: http://forum.unity3d.com/threads/331411)

Notes:
* The Unity Importer hasn't been cleaned up for general use, yet (i.e. it has a lot of project-specific code, and code that needs to be cleaned/simplified). This will come eventually, by way of lazy updating (i.e. only updating when old code causes issues or development slowdowns), but I can speed this up some if there's outside use for the package; at the moment, I'm only updating the importer portion of the repo occasionally, as it requires copying from my main game project.

Here's an example of a vmodel file's contents:
```
{^}
    objects:{^}
        Root:{^}
            position:[0 0 0]
            rotation:[0 0 0 1]
            scale:[1 1 1]
            children:{^}
                Armature:{^}
                    position:[0 0 .5]
                    rotation:[0 0 0 1]
                    scale:[1 1 1]
                    armature:{^}
                        bones:{^}
                            Bone:{position:[0 0 0] rotation:[0 0 0 1] scale:[1 1 1]}
                    animations:{^}
                        RollForward:{^}
                            fps:30
                            length:100
                            boneKeyframes:{^}
                                Bone:{^}
                                    0:{position:[0 0 0] rotation:[0 0 0 1] scale:[1 1 1]}
                                    100:{position:[0 0 -1] rotation:[-.707107 0 0 .707107] scale:[1 1 1]}
                Mesh:{^}
                    position:[0 0 .5]
                    rotation:[0 0 0 1]
                    scale:[1 1 1]
                    mesh:{^}
                        vertices:[^]
                            {position:[-.5 -.5 -.5] normal:[-.577349 -.577349 -.577349] uv_face0:[.666667 .333333] uv_face3:[.666667 .666667] uv_face4:[1 0] boneWeights:{Bone:1}}
                            {position:[-.5 .5 -.5] normal:[-.577349 .577349 -.577349] uv_face0:[.666667 0] uv_face1:[.333333 .666667] uv_face4:[1 .333333] boneWeights:{Bone:1}}
                            {position:[.5 .5 -.5] normal:[.577349 .577349 -.577349] uv_face1:[.333333 .333333] uv_face2:[.333333 .333333] uv_face4:[.666667 .333333] boneWeights:{Bone:1}}
                            {position:[.5 -.5 -.5] normal:[.577349 -.577349 -.577349] uv_face2:[.333333 0] uv_face3:[.333333 .666667] uv_face4:[.666667 0] boneWeights:{Bone:1}}
                            {position:[-.5 -.5 .5] normal:[-.577349 -.577349 .577349] uv_face0:[.333333 .333333] uv_face3:[.666667 .333333] uv_face5:[0 1] boneWeights:{Bone:1}}
                            {position:[-.5 .5 .5] normal:[-.577349 .577349 .577349] uv_face0:[.333333 0] uv_face1:[0 .666667] uv_face5:[.333333 1] boneWeights:{Bone:1}}
                            {position:[.5 .5 .5] normal:[.577349 .577349 .577349] uv_face1:[0 .333333] uv_face2:[0 .333333] uv_face5:[.333333 .666667] boneWeights:{Bone:1}}
                            {position:[.5 -.5 .5] normal:[.577349 -.577349 .577349] uv_face2:[0 0] uv_face3:[.333333 .333333] uv_face5:[0 .666667] boneWeights:{Bone:1}}
                        faces:[[1 0 4 5] [5 6 2 1] [6 7 3 2] [0 3 7 4] [0 1 2 3] [7 6 5 4]]
                        materials:[^]
                            {diffuseColor:"ffffff" texture:"MainTexture.png"}
                        armature:"Armature"
```